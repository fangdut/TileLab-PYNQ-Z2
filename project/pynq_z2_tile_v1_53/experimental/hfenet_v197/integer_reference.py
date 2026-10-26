"""Offline integer migration oracle; never used by the operator workstation.

Floating64 convolution is an exact audit of INTEGER MACs bounded below2**53.
Normalization, geometry, residual arithmetic and the decision use integers.
The hardware implementation and board qualification remain separate gates.
"""
from dataclasses import dataclass
import math,operator
import torch
import torch.nn.functional as F
from torch.fx import Interpreter

QMIN=-32768;QMAX=32767
def exponent(peak,margin=2):
    return int(math.ceil(math.log2(max(float(peak)*margin,2.0**-24)/QMAX)))
def rshift(x,shift):
    """Signed nearest-even power-of-two conversion, without floats."""
    if shift<=0:return x<<(-shift)
    if shift>=63:raise ValueError('Unsupported requant shift')
    mag=x.abs();base=mag>>shift;rem=mag-(base<<shift);half=1<<(shift-1)
    rounded=base+((rem>half)|((rem==half)&((base&1)!=0))).to(torch.int64)
    return torch.where(x<0,-rounded,rounded)
def round_div(num,den):
    if den<=0:raise ValueError('Positive denominator required')
    sign=-1 if num<0 else 1;q,r=divmod(abs(num),den)
    return sign*(q+int(2*r>den or (2*r==den and q&1)))
def scalar_shift(n,shift):return round_div(n,1<<shift) if shift>0 else n<<(-shift)

@dataclass
class QT:
    q:torch.Tensor
    exp:object

class Calibrator(Interpreter):
    def __init__(self,module):super().__init__(module);self.peaks={};self.shapes={}
    def run_node(self,node):
        out=super().run_node(node)
        if isinstance(out,torch.Tensor):
            v=out.detach();self.shapes[node.name]=list(v.shape)
            if node.op=='call_module' and isinstance(self.fetch_attr(node.target),torch.nn.Conv2d):
                peak=v.abs().amax(dim=(0,2,3)).double();old=self.peaks.get(node.name)
                self.peaks[node.name]=peak if old is None else torch.maximum(peak,old)
            else:
                peak=float(v.abs().max());self.peaks[node.name]=max(self.peaks.get(node.name,0),peak)
        return out
    def export(self):
        return dict(exponents={name:[exponent(v) for v in peak] if isinstance(peak,torch.Tensor) else exponent(peak) for name,peak in self.peaks.items()},shapes=self.shapes,margin=2,bits=16,rounding='nearest_even',normal_calibration_only=True)

class IntegerGraph(Interpreter):
    def __init__(self,module,calibration):
        super().__init__(module);self.cal=calibration;self.clipped={};self.weights={};self.norm_records=[];self.trace=[]
        for node in module.graph.nodes:
            if node.op=='call_module' and isinstance(self.fetch_attr(node.target),torch.nn.Conv2d):
                conv=self.fetch_attr(node.target);w=conv.weight.detach().double()
                if node.target=='featurefusion.Prewitt_Operator':exp=[0]*len(w);q=w.to(torch.int64);assert torch.equal(q.double(),w)
                else:
                    exp=[exponent(p,margin=1) for p in w.abs().flatten(1).amax(1)]
                    q=torch.stack([torch.round(v/(2.0**e)).to(torch.int64) for v,e in zip(w,exp)])
                assert int(q.abs().max())<=32767
                self.weights[node.name]=(q,exp)
    def clip(self,q,name):
        count=int(((q<QMIN)|(q>QMAX)).sum());self.clipped[name]=self.clipped.get(name,0)+count
        return q.clamp(QMIN,QMAX)
    def convert(self,x,exp,name):
        if isinstance(x.exp,list):
            q=torch.stack([rshift(x.q[:,c],exp-e) for c,e in enumerate(x.exp)],dim=1)
        else:q=rshift(x.q,exp-x.exp)
        return QT(self.clip(q,name),exp)
    def conv(self,node,module,x):
        if isinstance(x.exp,list):raise ValueError('Conv requires common activation scale')
        weight,wexp=self.weights[node.name]
        # At most800 products;16bit operands ensure every partial sum<2**40.
        terms=weight.shape[1]*weight.shape[2]*weight.shape[3]
        bound=terms*int(x.q.abs().max())*int(weight.abs().max())
        if bound>=2**53:raise ValueError('Float64 integer-MAC audit is no longer exact')
        mac=F.conv2d(x.q.double(),weight.double(),None,module.stride,module.padding,module.dilation,module.groups)
        if not torch.equal(mac,torch.round(mac)):raise ValueError('Noninteger MAC')
        mac=mac.to(torch.int64)
        exp=[0]*len(wexp) if node.target=='featurefusion.Prewitt_Operator' else self.cal['exponents'][node.name]
        q=torch.stack([rshift(mac[:,c],exp[c]-x.exp-wexp[c]) for c in range(len(exp))],dim=1)
        return QT(self.clip(q,node.name),0 if node.target=='featurefusion.Prewitt_Operator' else exp)
    def norm(self,node,module,x):
        n=x.q.shape[-1]*x.q.shape[-2];out_exp=self.cal['exponents'][node.name];q=x.q
        sums=q.sum((0,2,3));squares=(q*q).sum((0,2,3));a=[];b=[];records=[]
        for c in range(q.shape[1]):
            sx=x.exp[c] if isinstance(x.exp,list) else x.exp
            eps=int(round(module.eps*n*n*(2.0**(-2*sx))))
            variance=n*int(squares[c])-int(sums[c])**2+eps
            if variance<0:raise ValueError('Negative integer variance')
            root=math.isqrt(variance);gamma=int(round(float(module.weight[c])*2**30));beta=int(round(float(module.bias[c])*2**30))
            e=6-out_exp
            numerator=gamma<<e if e>=0 else gamma;denominator=root if e>=0 else root<<(-e)
            aa=round_div(numerator,denominator) if root else 0
            bb=scalar_shift(beta,-e);a.append(aa);b.append(bb)
            maxdiff=int((n*q[:,c]-sums[c]).abs().max())
            if maxdiff*abs(aa)+abs(bb)>=2**63:raise OverflowError('Norm audit needs wider integer products')
            records.append(dict(channel=c,n=n,input_exp=sx,output_exp=out_exp,sum=int(sums[c]),sumsq=int(squares[c]),epsilon=eps,variance=variance,root=root,a=aa,b=bb,constant=(root==0)))
        av=torch.tensor(a,dtype=torch.int64)[None,:,None,None];bv=torch.tensor(b,dtype=torch.int64)[None,:,None,None]
        diff=n*q-sums[None,:,None,None];out=rshift(diff*av+bv,36)
        self.norm_records.append(dict(node=node.name,channels=records))
        return QT(self.clip(out,node.name),out_exp)
    def run_node(self,node):
        if node.op=='placeholder':
            value=super().run_node(node)
            if not torch.equal(value,value.round()):raise ValueError('Input must be original integer channels')
            return QT(value.to(torch.int64),0)
        args,kwargs=self.fetch_args_kwargs_from_env(node)
        if node.op=='output':return args[0]
        if node.op=='call_module':
            module=self.fetch_attr(node.target);x=args[0]
            if isinstance(module,torch.nn.Conv2d):out=self.conv(node,module,x)
            elif isinstance(module,torch.nn.InstanceNorm2d):out=self.norm(node,module,x)
            elif isinstance(module,torch.nn.ReLU):out=self.convert(QT(x.q.clamp_min(0),x.exp),self.cal['exponents'][node.name],node.name)
            elif isinstance(module,torch.nn.MaxPool2d):
                if module.kernel_size!=2 or module.stride!=2:raise ValueError('Unsupported pool')
                q=x.q;h,w=q.shape[-2:];out=QT(q.reshape(*q.shape[:-2],h//2,2,w//2,2).amax(dim=(-1,-3)),x.exp)
            elif isinstance(module,torch.nn.Upsample):
                if module.scale_factor!=2 or module.mode!='bilinear' or module.align_corners is not False:raise ValueError('Unsupported resize')
                q=x.q;h,w=q.shape[-2:];ix=torch.arange(2*w);base=((ix-1)//2).clamp(0,w-1);nxt=((ix+1)//2).clamp(0,w-1);weight=torch.where(ix%2==0,3,1)
                horizontal=q[...,base]*(4-weight)+q[...,nxt]*weight
                iy=torch.arange(2*h);base=((iy-1)//2).clamp(0,h-1);nxt=((iy+1)//2).clamp(0,h-1);weight=torch.where(iy%2==0,3,1)[:,None]
                value=horizontal[...,base,:]*(4-weight)+horizontal[...,nxt,:]*weight
                out=self.convert(QT(value,x.exp-4),self.cal['exponents'][node.name],node.name)
            elif isinstance(module,torch.nn.Sigmoid):out=QT((x.q>0).to(torch.int64),0)
            else:raise ValueError('Unsupported module '+str(type(module)))
        elif node.op=='call_function' and node.target is operator.add:
            x,y=args;exp=min(x.exp,y.exp);q=(x.q<<(x.exp-exp))+(y.q<<(y.exp-exp))
            out=self.convert(QT(q,exp),self.cal['exponents'][node.name],node.name)
        elif node.op=='call_function' and node.target is torch.cat:
            items=args[0];exp=0 if node.name=='cat' else self.cal['exponents'][node.name]
            out=QT(torch.cat([self.convert(x,exp,node.name).q for x in items],dim=kwargs.get('dim',1)),exp)
        else:raise ValueError('Unsupported FX node '+str(node))
        self.trace.append(dict(node=node.name,shape=list(out.q.shape),exp=out.exp))
        return out
