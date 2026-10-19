"""Frozen directional-mean profile against portable, exposed development data."""
from pathlib import Path
import argparse,hashlib,json,sys,time
import numpy as np
R=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(R/'models'),str(R/'scripts')]
from evaluate_ridge_v154 import cohort,load,sha
from directional_mean_reference import directional_mean_score,mask_from_scores
from valley_reference import valley
from regions_reference import regions

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    models=[R/'models'/n for n in ('directional_mean_reference.py','ridge_reference.py','valley_reference.py','weak_reference.py','regions_reference.py')]
    code=[Path(__file__),R/'scripts/evaluate_ridge_v154.py']+models
    snapshot=args.out/'source';snapshot.mkdir()
    for p in code:(snapshot/p.name).write_bytes(p.read_bytes())
    declaration=dict(profile=dict(valley_high=90,valley_low=45,short_high=40,short_low=20,long_high=48,long_low=24,passes=4,support=3),
        scope='OFFLINE EXPOSED DEVELOPMENT, fixed after parameter exploration; NOT blind accuracy or a new board test',
        hardware_acceptance=False,source_sha256={str(p.relative_to(R)):sha(p) for p in code})
    (args.out/'declaration.json').write_text(json.dumps(declaration,indent=2)+'\n')
    rows=[];sources=[];start=time.time()
    for i,(ds,sid,label,p,truth,m) in enumerate(cohort()):
        rgb=load(p);a=rgb.astype(np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
        keep=np.zeros(gray.shape,bool);keep[80:640,80:1200]=True
        features=(valley(gray,8),valley(gray,16),directional_mean_score(gray,8),directional_mean_score(gray,16))
        sources.append(dict(dataset=ds,id=sid,image=str(p.relative_to(R)),sha256=sha(p),mask_sha256=sha(m) if m else None))
        for enabled in (False,True):
            mask=mask_from_scores(*features,keep,enabled);rr=regions(mask)
            rows.append(dict(dataset=ds,id=sid,label=label,variant='mean_v154' if enabled else 'accepted_v152',
                alarm=bool(rr['boxes'] or rr['overflow']),tp=int((mask&truth).sum()),fp=int((mask&~truth).sum()),fn=int((~mask&truth).sum()),boxes=rr['boxes']))
        if i%40==0:print(json.dumps(dict(images=i+1,elapsed_s=round(time.time()-start,1))),flush=True)
    summary=[]
    for ds in sorted({r['dataset'] for r in rows}):
        for name in ('accepted_v152','mean_v154'):
            g=[r for r in rows if r['dataset']==ds and r['variant']==name]
            tp=sum(r['tp'] for r in g);fp=sum(r['fp'] for r in g);fn=sum(r['fn'] for r in g)
            summary.append(dict(dataset=ds,variant=name,images=len(g),crack_images=sum(r['label']=='crack' for r in g),normal_images=sum(r['label']=='good' for r in g),
                crack_alarms=sum(r['label']=='crack' and r['alarm'] for r in g),normal_alarms=sum(r['label']=='good' and r['alarm'] for r in g),
                pixel_recall=tp/(tp+fn) if tp+fn else None,pixel_precision=tp/(tp+fp) if tp+fp else None,tp=tp,fp=fp,fn=fn))
    result=dict(**declaration,elapsed_s=time.time()-start,summary=summary,sources=sources,rows=rows)
    (args.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
