"""Freeze all-integer deployment reference, including preprocessing and head.

CPU is used solely for offline design/calibration/verification. Deployment
acceptance requires independent RTL and physical-board results.
"""
from pathlib import Path
import argparse, json, math, time
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from evaluate_lightweight import MobileGraph, rq, round_away, save, sha

class FixedGraph(MobileGraph):
    def image(self,path):
        if not getattr(self,'fixed_input',False):return super().image(path)
        with Image.open(path) as im:a=torch.from_numpy(np.array(im.convert('RGB'),copy=True)).to(torch.int64)
        h,w,_=a.shape; d=2*self.side
        xx=((2*torch.arange(self.side)+1)*w-self.side).clamp(0,(w-1)*d)
        yy=((2*torch.arange(self.side)+1)*h-self.side).clamp(0,(h-1)*d)
        x0=xx//d; y0=yy//d; fx=xx%d; fy=yy%d
        x1=(x0+1).clamp(max=w-1); y1=(y0+1).clamp(max=h-1)
        s=(a[y0[:,None],x0[None,:]]*(d-fx)[None,:,None]*(d-fy)[:,None,None]+
           a[y0[:,None],x1[None,:]]*fx[None,:,None]*(d-fy)[:,None,None]+
           a[y1[:,None],x0[None,:]]*(d-fx)[None,:,None]*fy[:,None,None]+
           a[y1[:,None],x1[None,:]]*fx[None,:,None]*fy[:,None,None])
        m=torch.tensor(self.input_m,dtype=torch.int64); b=torch.tensor(self.input_b,dtype=torch.int64)
        p=s*m+b; q=(torch.sign(p)*((p.abs()+(1<<47))>>48)).clamp(-127,127).to(torch.int32)
        # Parent integer forward divides by input scale; integral q values
        # survive this float representation roundtrip exactly on [-127,127].
        return q.permute(2,0,1)[None].float()*self.scales[0]

def project(codes,weights,bias,shift):
    x=codes.to(torch.int64)@weights.to(torch.int64)+bias
    if shift:x=torch.sign(x)*((x.abs()+(1<<(shift-1)))>>shift)
    return x.clamp(-32767,32767).to(torch.int32)

def integer_scores(query,centers,grid):
    # All intermediate squared distances are integers below 2**53, so float64
    # dot products are EXACT here. The RTL uses signed integer multiplies.
    cn=(centers.double()**2).sum(1)[None,:]; raw=[]
    for q in query.split(128):
        q=q.double(); d=((q*q).sum(1)[:,None]+cn-2*q@centers.double().T).clamp(min=0)
        raw.append(torch.floor(torch.sqrt(d.min(1).values)).to(torch.int64))
    raw=torch.cat(raw).reshape(1,1,grid,grid)
    # float64 again represents every sum exactly; /9 rounded by integer math.
    padded=F.pad(raw.double(),(1,1,1,1),mode='replicate')
    sums=round_away(F.avg_pool2d(padded,3,1)*9).to(torch.int64)
    return ((sums+4)//9)[0,0].to(torch.int32)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--weights',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--side',type=int,default=224);p.add_argument('--centers',type=int,default=1024)
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=False); (a.out/'codes').mkdir()
    torch.set_num_threads(8);torch.manual_seed(170); started=time.perf_counter()
    rows=json.loads((a.dataset/'manifest.json').read_text(encoding='utf8'))['images']
    memory=[r for r in rows if r['role']=='memory']; cal=[r for r in rows if r['role']=='calibration']; test=[r for r in rows if r['role']=='test']
    graph=FixedGraph(a.weights,a.side)
    for r in memory[:32]:graph.forward(a.dataset/r['file'],calibrate=True)
    graph.freeze(a.out)
    d=2*a.side; qscale=graph.scales[0]
    graph.input_m=[int(np.floor((1<<48)/(d*d*255*std*qscale)+.5)) for std in [.229,.224,.225]]
    graph.input_b=[int(round(-mean/(std*qscale)*(1<<48))) for mean,std in zip([.485,.456,.406],[.229,.224,.225])]
    graph.fixed_input=True; codes={}; patches=[]; gen=torch.Generator().manual_seed(1682026)
    protocol=dict(version='V170_INTEGER_REFERENCE',backbone='MobileNetV2 features0-13',side=a.side,grid=a.side//8,
        cnn_arithmetic='INT8 weights/activation, INT32 accumulators, INT64 Q28 requantization',
        input_arithmetic='rational bilinear RGB and affine INT64 Q48 normalization',
        head_arithmetic='INT8 pooled features, INT16 PCA/codebook, integer squared distance, integer square root and smoothing',
        memory_ids=[r['id'] for r in memory],activation_ids=[r['id'] for r in memory[:32]],
        threshold_ids=[r['id'] for r in cal],test_labels_used_for_fit=False,benchmark_is_blind=False,
        board_verified=False,source_sha256=sha(Path(__file__)),graph_source_sha256=sha(Path(__file__).with_name('evaluate_lightweight.py')),
        weights_sha256=sha(a.weights),manifest_sha256=sha(a.dataset/'manifest.json'))
    save(a.out/'protocol.json',protocol)
    for i,r in enumerate(memory+cal+test):
        c=graph.forward(a.dataset/r['file'],integer=True,output_codes=True); codes[r['id']]=c
        np.save(a.out/'codes'/(r['id']+'.npy'),c.numpy().astype('i1'),allow_pickle=False)
        if r['role']=='memory':patches.append(c[torch.randperm(len(c),generator=gen)[:64]].clone())
        if (i+1)%30==0:print(f'Exact integer features {i+1}/{len(rows)} {time.perf_counter()-started:.1f}s',flush=True)
    bank=torch.cat(patches)
    scales=torch.tensor([graph.scales[graph.fa]]*32+[graph.scales[graph.fb]]*96)
    features=bank.float()*scales;mean=features.mean(0)
    _,_,basis=torch.pca_lowrank(features,q=64,center=True,niter=4)
    coeff=basis*scales[:,None]; weight_scale=float(coeff.abs().max())/32767
    pw=round_away(coeff/weight_scale).to(torch.int32)
    bias=round_away((-mean@basis).double()/weight_scale).to(torch.int64)
    expected=(features-mean)@basis
    shift=max(0,math.ceil(math.log2(max(float(expected.abs().max())/(weight_scale*16000),1))))
    projected=project(bank,pw,bias,shift);nearest=torch.full((len(bank),),float('inf'),dtype=torch.float64)
    selected=[];index=0
    for _ in range(a.centers):
        selected.append(index); nearest=torch.minimum(nearest,((projected.double()-projected[index].double())**2).sum(1)); index=int(nearest.argmax())
    centers=projected[selected].contiguous();grid=a.side//8;normal=[]
    for r in cal:
        scores=integer_scores(project(codes[r['id']],pw,bias,shift),centers,grid)
        normal.append(dict(id=r['id'],score=int(scores.max())))
    threshold=int(np.floor(np.quantile([r['score'] for r in normal],.95)))+1
    np.savez_compressed(a.out/'integer_head.npz',projection=pw.numpy().astype('<i2'),bias=bias.numpy(),
        centers=centers.numpy().astype('<i2'),shift=np.array(shift),input_m=np.array(graph.input_m),input_b=np.array(graph.input_b),
        physical_scale=np.array(weight_scale*(1<<shift)),threshold=np.array(threshold))
    save(a.out/'normal_calibration.json',normal);results=[]
    for r in test:
        q=project(codes[r['id']],pw,bias,shift);s=integer_scores(q,centers,grid);score=int(s.max())
        np.save(a.out/(r['id']+'_scores.npy'),s.numpy(),allow_pickle=False)
        results.append(dict(id=r['id'],label=r['label'],score=score,alarm=score>threshold,expected=r['label']!='good',
            projection_clipped_values=int((q.abs()==32767).sum())))
    tp=sum(r['alarm'] and r['expected'] for r in results);fp=sum(r['alarm'] and not r['expected'] for r in results)
    save(a.out/'results.json',results)
    summary=dict(tp=tp,fp=fp,fn=84-tp,tn=33-fp,accuracy=(tp+33-fp)/117,recall=tp/84,
        cracks_detected=sum(r['alarm'] for r in results if r['label']=='crack'),threshold=threshold,
        projection_shift=shift,projection_scale=weight_scale*(1<<shift),cnn_macs_per_frame=graph.macs,
        projection_clipped_values=sum(r['projection_clipped_values'] for r in results),
        board_verified=False,rtl_verified=False,all_integer_reference=True,elapsed_seconds=time.perf_counter()-started)
    save(a.out/'summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
