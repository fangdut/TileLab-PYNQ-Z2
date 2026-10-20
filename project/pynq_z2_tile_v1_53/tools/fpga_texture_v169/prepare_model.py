"""Offline normal-only compression for a fully FPGA-executed inference graph."""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from torchvision.models import wide_resnet50_2

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def folded_network(weights):
    model=wide_resnet50_2(weights=None);model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True));model.eval()
    def fuse(parent,conv_name,bn_name):
        conv=getattr(parent,conv_name);bn=getattr(parent,bn_name)
        with torch.no_grad():
            scale=bn.weight/torch.sqrt(bn.running_var+bn.eps)
            conv.weight.copy_(conv.weight*scale[:,None,None,None])
            conv.bias=torch.nn.Parameter(bn.bias-bn.running_mean*scale)
        setattr(parent,bn_name,torch.nn.Identity())
    fuse(model,'conv1','bn1')
    for stage in [model.layer1,model.layer2,model.layer3]:
        for block in stage:
            for i in [1,2,3]:fuse(block,'conv'+str(i),'bn'+str(i))
            if block.downsample is not None:fuse(block.downsample,'0','1')
    return model

@torch.inference_mode()
def features(model,path,side=448):
    with Image.open(path) as im:a=np.array(im.convert('RGB'),copy=True)
    x=torch.from_numpy(a).permute(2,0,1)[None].float()/255
    x=F.interpolate(x,size=(side,side),mode='bilinear',align_corners=False,antialias=False)
    x=(x-torch.tensor([.485,.456,.406])[None,:,None,None])/torch.tensor([.229,.224,.225])[None,:,None,None]
    x=model.maxpool(model.relu(model.bn1(model.conv1(x))));x=model.layer1(x);a=model.layer2(x);b=model.layer3(a)
    a=F.avg_pool2d(a,3,1,1);b=F.avg_pool2d(b,3,1,1);b=F.interpolate(b,size=a.shape[-2:],mode='bilinear',align_corners=False)
    return torch.cat([a,b],1)[0].permute(1,2,0).reshape(-1,1536).contiguous()

@torch.inference_mode()
def distances(q,centers,grid=56):
    cn=(centers*centers).sum(1)[None,:];out=[]
    for x in q.split(256):out.append(torch.sqrt(torch.clamp(((x*x).sum(1)[:,None]+cn-2*x@centers.T).min(1).values,min=0)))
    raw=torch.cat(out).reshape(1,1,grid,grid)
    return F.avg_pool2d(F.pad(raw,(1,1,1,1),mode='replicate'),3,1)[0,0]

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--weights',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(8);torch.manual_seed(169)
    data=json.loads((a.dataset/'manifest.json').read_text(encoding='utf8'));model=folded_network(a.weights)
    memory=[r for r in data['images'] if r['role']=='memory'];cal=[r for r in data['images'] if r['role']=='calibration']
    assert len(memory)==180 and len(cal)==50 and all(r['label']=='good' and r['split']=='train' for r in memory+cal)
    save(a.output/'fit_protocol.json',dict(input_side=448,feature_dimensions=1536,projection_dimensions=64,centers=1024,
        memory_ids=[r['id'] for r in memory],normal_calibration_ids=[r['id'] for r in cal],
        preprocessing='PL-equivalent float bilinear resize, align_corners=False, no antialias; normalized in PL',
        backbone='WideResNet50-2 layer1-3 with folded BN; full network on PL',
        selection='PCA64 then greedy k-center1024 on normal patches only',
        threshold='normal calibration empirical95 percentile',test_labels_used_for_fit=False,
        source_code_sha256=sha(__file__),pretrained_sha256=sha(a.weights),benchmark_is_new_independent_holdout=False))
    patches=[];generator=torch.Generator().manual_seed(1682026)
    for i,r in enumerate(memory):
        f=features(model,a.dataset/r['file']);patches.append(f[torch.randperm(len(f),generator=generator)[:64]].clone())
        if (i+1)%30==0:print(f'Hardware feature bank {i+1}/180',flush=True)
    bank=torch.cat(patches);mean=bank.mean(0)
    _,_,basis=torch.pca_lowrank(bank,q=64,center=True,niter=4)
    projected=(bank-mean)@basis
    # Greedy covering set, using only nominal descriptors.
    selected=[];nearest=torch.full((len(projected),),float('inf'));index=0
    for i in range(1024):
        selected.append(index);distance=((projected-projected[index])**2).sum(1)
        nearest=torch.minimum(nearest,distance);index=int(nearest.argmax())
    centers=projected[selected].contiguous()
    np.savez_compressed(a.output/'compression.npz',mean=mean.numpy(),projection=basis.numpy(),centers=centers.numpy())
    torch.save({k:v for k,v in model.state_dict().items() if not k.startswith(('layer4.','fc.'))},a.output/'folded_feature_weights.pt')
    normal=[]
    for i,r in enumerate(cal):
        q=(features(model,a.dataset/r['file'])-mean)@basis;scores=distances(q,centers)
        normal.append(dict(id=r['id'],score=float(scores.max())))
    threshold=float(np.quantile([r['score'] for r in normal],.95))+1e-6
    save(a.output/'normal_calibration.json',normal)
    save(a.output/'model.json',dict(version='V169-FP32-PCA64-KCENTER1024',threshold=threshold,
        compression_sha256=sha(a.output/'compression.npz'),folded_weights_sha256=sha(a.output/'folded_feature_weights.pt'),
        threshold_test_labels_used=False,fpga_verified=False,pretrained_sha256=sha(a.weights)))
    rows=[]
    for i,r in enumerate([r for r in data['images'] if r['role']=='test']):
        q=(features(model,a.dataset/r['file'])-mean)@basis;scores=distances(q,centers);score=float(scores.max())
        rows.append(dict(id=r['id'],label=r['label'],score=score,alarm=score>threshold,expected=r['label']!='good'))
        np.save(a.output/(r['id']+'_scores.npy'),scores.numpy(),allow_pickle=False)
        if (i+1)%20==0:print(f'Compressed-model real benchmark {i+1}/117',flush=True)
    tp=sum(r['alarm'] and r['expected'] for r in rows);fp=sum(r['alarm'] and not r['expected'] for r in rows)
    summary=dict(tp=tp,fp=fp,fn=84-tp,tn=33-fp,accuracy=(tp+33-fp)/117,recall=tp/84,false_positive_rate=fp/33,
        cracks_detected=sum(r['alarm'] for r in rows if r['label']=='crack'),threshold=threshold,
        interpretation='Offline migration reference only, not board evidence')
    save(a.output/'results.json',rows);save(a.output/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
