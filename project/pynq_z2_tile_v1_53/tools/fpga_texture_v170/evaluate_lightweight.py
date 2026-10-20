"""OFFLINE design exploration; never imported by the board runtime.

Normal-only bank/calibration. Integer mode uses real int32 convolutions and
int64 fixed-point requantization, rather than pretending float is INT8 hardware.
Historical test images are an exposed development benchmark, not a blind test.
"""
from pathlib import Path
import argparse, hashlib, json, time
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from torchvision.models import resnet18, ResNet18_Weights, mobilenet_v2, MobileNet_V2_Weights

def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def round_away(x):
    return torch.sign(x)*torch.floor(torch.abs(x)+.5)

def rq(x, multiplier, shift=28):
    """Signed rounding to nearest; ties away from zero. No float at runtime."""
    p=x.to(torch.int64)*multiplier
    return (torch.sign(p)*((p.abs()+(1<<(shift-1)))>>shift)).to(torch.int32)

class Graph:
    def __init__(self, weights, side, stages=(2,3)):
        self.net=resnet18(weights=None)
        self.net.load_state_dict(torch.load(weights, map_location='cpu', weights_only=True))
        self.net.eval(); self.nodes=[]; self.side=side; self.maxima={}; self.quant={}
        def conv(src, m, bn, relu):
            scale=bn.weight.detach()/torch.sqrt(bn.running_var.detach()+bn.eps)
            w=m.weight.detach()*scale[:,None,None,None]
            b=bn.bias.detach()-bn.running_mean.detach()*scale
            self.nodes.append(dict(kind='conv', inputs=[src], weight=w, bias=b,
                stride=m.stride[0], pad=m.padding[0], relu=relu))
            return len(self.nodes)
        def node(kind, sources):
            self.nodes.append(dict(kind=kind, inputs=sources)); return len(self.nodes)
        x=conv(0,self.net.conv1,self.net.bn1,True); x=node('maxpool',[x])
        for si,stage in enumerate([self.net.layer1,self.net.layer2,self.net.layer3][:stages[1]],1):
            for block in stage:
                skip=x; z=conv(x,block.conv1,block.bn1,True)
                z=conv(z,block.conv2,block.bn2,False)
                if block.downsample is not None:
                    skip=conv(skip,block.downsample[0],block.downsample[1],False)
                x=node('addrelu',[z,skip])
            if si==stages[0]:self.fa=x
        self.fb=x; self.scales={}; self.feature_dim=64*2**(stages[0]-1)+64*2**(stages[1]-1)

    def image(self, path):
        with Image.open(path) as im: a=np.array(im.convert('RGB'),copy=True)
        x=torch.from_numpy(a).permute(2,0,1)[None].float()/255
        x=F.interpolate(x,size=(self.side,self.side),mode='bilinear',align_corners=False,antialias=False)
        return (x-torch.tensor([.485,.456,.406])[None,:,None,None])/torch.tensor([.229,.224,.225])[None,:,None,None]

    @torch.inference_mode()
    def forward(self, path, integer=False, calibrate=False, output_codes=False):
        x=self.image(path)
        values={0:round_away(x/self.scales[0]).clamp(-127,127).to(torch.int32) if integer else x}
        if calibrate:self.maxima[0]=max(self.maxima.get(0,0),float(x.abs().max()))
        macs=0
        for i,n in enumerate(self.nodes,1):
            x=values[n['inputs'][0]]
            if n['kind']=='conv':
                if integer:
                    q=self.quant[i]
                    x=F.conv2d(x,q['weight'],q['bias'],stride=n['stride'],padding=n['pad'],groups=n.get('groups',1))
                    x=rq(x,q['multiplier'][None,:,None,None])
                    x=x.clamp(0 if n['relu'] else -127,127)
                    if n.get('relu6'):x=x.clamp(max=min(127,int(np.floor(6/self.scales[i]+.5))))
                else:
                    x=F.conv2d(x,n['weight'],n['bias'],stride=n['stride'],padding=n['pad'],groups=n.get('groups',1))
                    if n['relu']:x=x.relu()
                    if n.get('relu6'):x=x.clamp(max=6)
                macs+=x.numel()*int(np.prod(n['weight'].shape[1:]))
            elif n['kind']=='maxpool':
                # Exact: all int8 values are exactly representable as float32.
                x=F.max_pool2d(x.float(),3,2,1)
                if integer:x=x.to(torch.int32)
            else:
                y=values[n['inputs'][1]]
                if integer:
                    qa,qb=self.quant[i]['multipliers']
                    x=(rq(x,qa)+rq(y,qb)).clamp(0 if n['kind']=='addrelu' else -127,127)
                else:
                    x=x+y
                    if n['kind']=='addrelu':x=x.relu()
            values[i]=x
            if calibrate:self.maxima[i]=max(self.maxima.get(i,0),float(x.abs().max()))
        self.macs=macs
        a=values[self.fa].float(); b=values[self.fb].float()
        if output_codes:
            assert integer
            a=round_away(F.avg_pool2d(a,3,1,1)); b=round_away(F.avg_pool2d(b,3,1,1))
            b=round_away(F.interpolate(b,size=a.shape[-2:],mode='bilinear',align_corners=False))
            return torch.cat([a,b],1)[0].permute(1,2,0).reshape(-1,self.feature_dim).to(torch.int32).contiguous()
        if integer:a*=self.scales[self.fa]; b*=self.scales[self.fb]
        a=F.avg_pool2d(a,3,1,1); b=F.avg_pool2d(b,3,1,1)
        b=F.interpolate(b,size=a.shape[-2:],mode='bilinear',align_corners=False)
        return torch.cat([a,b],1)[0].permute(1,2,0).reshape(-1,self.feature_dim).contiguous()

    def freeze(self, folder):
        self.scales={i:max(v*1.05/127,1e-9) for i,v in self.maxima.items()}
        for i,n in enumerate(self.nodes,1):
            if n['kind']=='maxpool':self.scales[i]=self.scales[n['inputs'][0]]
            if n['kind']=='conv':
                ws=n['weight'].abs().flatten(1).max(1).values.clamp(min=1e-9)/127
                qw=round_away(n['weight']/ws[:,None,None,None]).clamp(-127,127).to(torch.int32)
                scale=self.scales[n['inputs'][0]]*ws
                bias=round_away(n['bias']/scale).to(torch.int32)
                m=round_away(scale.double()/self.scales[i]*(1<<28)).to(torch.int64)
                self.quant[i]=dict(weight=qw,bias=bias,multiplier=m,weight_scale=ws)
            elif n['kind'] in ('addrelu','add'):
                self.quant[i]=dict(multipliers=[int(np.floor(self.scales[k]/self.scales[i]*(1<<28)+.5)) for k in n['inputs']])
        torch.save(dict(nodes=self.nodes,scales=self.scales,quant=self.quant,fa=self.fa,fb=self.fb,side=self.side),folder/'quantized_graph.pt')

class MobileGraph(Graph):
    def __init__(self,weights,side,stages=None):
        self.net=mobilenet_v2(weights=None)
        self.net.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True))
        self.net.eval(); self.nodes=[]; self.side=side; self.maxima={}; self.quant={}; self.scales={}
        def conv(src, seq):
            m,bn=seq[0],seq[1]; scale=bn.weight.detach()/torch.sqrt(bn.running_var.detach()+bn.eps)
            self.nodes.append(dict(kind='conv',inputs=[src],weight=m.weight.detach()*scale[:,None,None,None],
                bias=bn.bias.detach()-bn.running_mean.detach()*scale,stride=m.stride[0],pad=m.padding[0],
                groups=m.groups,relu=len(seq)>2,relu6=len(seq)>2))
            return len(self.nodes)
        x=conv(0,self.net.features[0])
        for i,block in enumerate(self.net.features[1:14],1):
            skip=x; seq=block.conv; j=0
            while j<len(seq):
                if isinstance(seq[j],torch.nn.Conv2d):
                    x=conv(x,seq[j:j+2]); j+=2
                else:x=conv(x,seq[j]); j+=1
            if block.use_res_connect:
                self.nodes.append(dict(kind='add',inputs=[x,skip])); x=len(self.nodes)
            if i==6:self.fa=x
        self.fb=x; self.feature_dim=128

@torch.inference_mode()
def distances(q, centers, grid):
    cn=(centers*centers).sum(1)[None,:]; out=[]
    for x in q.split(256):
        out.append(torch.sqrt(torch.clamp(((x*x).sum(1)[:,None]+cn-2*x@centers.T).min(1).values,min=0)))
    raw=torch.cat(out).reshape(1,1,grid,grid)
    return F.avg_pool2d(F.pad(raw,(1,1,1,1),mode='replicate'),3,1)[0,0]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True); p.add_argument('--weights',type=Path,required=True)
    p.add_argument('--side',type=int,default=224); p.add_argument('--integer',action='store_true')
    p.add_argument('--dim',type=int,default=32); p.add_argument('--centers',type=int,default=512)
    p.add_argument('--stages',choices=['1,2','2,3'],default='2,3')
    p.add_argument('--backbone',choices=['resnet18','mobilenet_v2'],default='resnet18')
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(8); torch.manual_seed(170)
    if not a.weights.exists():
        a.weights.parent.mkdir(parents=True,exist_ok=True)
        # Official Torch URL with filename SHA256 prefix verification.
        weight_enum=ResNet18_Weights.DEFAULT if a.backbone=='resnet18' else MobileNet_V2_Weights.DEFAULT
        prefix=weight_enum.url.rsplit('-',1)[1].split('.')[0]
        torch.hub.download_url_to_file(weight_enum.url,str(a.weights),hash_prefix=prefix)
    data=json.loads((a.dataset/'manifest.json').read_text(encoding='utf8'))
    memory=[r for r in data['images'] if r['role']=='memory']; cal=[r for r in data['images'] if r['role']=='calibration']
    test=[r for r in data['images'] if r['role']=='test']
    assert len(memory)==180 and len(cal)==50 and all(r['split']=='train' and r['label']=='good' for r in memory+cal)
    stages=tuple(map(int,a.stages.split(',')))
    graph=(Graph if a.backbone=='resnet18' else MobileGraph)(a.weights,a.side,stages)
    grid=a.side//(2**(stages[0]+1)) if a.backbone=='resnet18' else a.side//8
    # Preselect first 32 normal MEMORY images; calibration/test are not used for activation ranges.
    if a.integer:
        for r in memory[:32]:graph.forward(a.dataset/r['file'],calibrate=True)
        graph.freeze(a.out)
    save(a.out/'protocol.json',dict(backbone=('ResNet18 layers1-'+str(stages[1])) if a.backbone=='resnet18' else 'MobileNetV2 features0-13',feature_stages=stages,side=a.side,dim=a.dim,centers=a.centers,
        mode='INT8 weights/activations; exact int32 convolutions, int64 Q28 requant' if a.integer else 'FP32 design reference',
        activation_calibration_ids=[r['id'] for r in memory[:32]] if a.integer else [],
        memory_ids=[r['id'] for r in memory],threshold_calibration_ids=[r['id'] for r in cal],
        test_labels_used_for_fit=False,benchmark_is_blind=False,board_verified=False,
        weights_sha256=sha(a.weights),dataset_manifest_sha256=sha(a.dataset/'manifest.json'),source_sha256=sha(Path(__file__))))
    patches=[]; gen=torch.Generator().manual_seed(1682026); started=time.perf_counter()
    for i,r in enumerate(memory):
        f=graph.forward(a.dataset/r['file'],integer=a.integer)
        patches.append(f[torch.randperm(len(f),generator=gen)[:64]].clone())
        if (i+1)%30==0:print(f'Normal memory {i+1}/180 {time.perf_counter()-started:.1f}s',flush=True)
    bank=torch.cat(patches); mean=bank.mean(0); _,_,basis=torch.pca_lowrank(bank,q=a.dim,center=True,niter=4)
    projected=(bank-mean)@basis; nearest=torch.full((len(projected),),float('inf')); selected=[]; index=0
    for _ in range(a.centers):
        selected.append(index); nearest=torch.minimum(nearest,((projected-projected[index])**2).sum(1)); index=int(nearest.argmax())
    centers=projected[selected].contiguous()
    np.savez_compressed(a.out/'compression.npz',mean=mean.numpy(),projection=basis.numpy(),centers=centers.numpy())
    normal=[]
    for r in cal:
        f=graph.forward(a.dataset/r['file'],integer=a.integer); s=distances((f-mean)@basis,centers,grid)
        normal.append(dict(id=r['id'],score=float(s.max())))
    threshold=float(np.quantile([r['score'] for r in normal],.95))+1e-6
    save(a.out/'normal_calibration.json',normal); rows=[]
    for i,r in enumerate(test):
        f=graph.forward(a.dataset/r['file'],integer=a.integer); s=distances((f-mean)@basis,centers,grid); score=float(s.max())
        rows.append(dict(id=r['id'],label=r['label'],score=score,alarm=score>threshold,expected=r['label']!='good'))
        np.save(a.out/(r['id']+'_scores.npy'),s.numpy(),allow_pickle=False)
        if (i+1)%20==0:print(f'Historical real-photo benchmark {i+1}/{len(test)}',flush=True)
    tp=sum(r['alarm'] and r['expected'] for r in rows); fp=sum(r['alarm'] and not r['expected'] for r in rows)
    save(a.out/'results.json',rows)
    summary=dict(tp=tp,fp=fp,fn=84-tp,tn=33-fp,accuracy=(tp+33-fp)/117,recall=tp/84,
        cracks_detected=sum(r['alarm'] for r in rows if r['label']=='crack'),threshold=threshold,
        cnn_macs_per_frame=graph.macs,reduction_vs_v169=36746493952/graph.macs,
        ideal_cnn_seconds_128mac_100mhz=graph.macs/(128*100e6),
        hardware_timing_is_measured=False,board_verified=False,elapsed_seconds=time.perf_counter()-started)
    save(a.out/'summary.json',summary); print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
