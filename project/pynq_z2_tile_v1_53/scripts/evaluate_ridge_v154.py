"""Reproducible full-raster development ablation; no board/network control.

Historical HDMI-acquired RGB and source RGB stay in separate cohorts. All
cohorts are exposed development data. No new industrial accuracy is inferred.
"""
from pathlib import Path
import argparse,hashlib,json,sys,time,platform
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'models'))
from valley_reference import valley
from ridge_reference import ridge_score,mask_from_scores
from regions_reference import regions


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):
    with Image.open(path) as im:return np.asarray(im.convert('RGB'))
def cohort():
    src={a['id']:a for a in json.loads((R/'data/real_tiles/manifest.json').read_text())['samples']}
    for a in json.loads((R/'data/real_tiles/hdmi_manifest.json').read_text())['items']:
        if a['label'] not in ('crack','good'):continue
        p=R/'validation/reference_rgb'/f"real_{a['index']:03d}_original.png"
        truth=np.zeros((720,1280),bool);m=None
        if src[a['id']].get('mask'):
            m=R/'data/real_tiles'/src[a['id']]['mask']
            with Image.open(m) as im:truth[110:610,390:890]=np.asarray(im.convert('L').resize((500,500),Image.Resampling.NEAREST))>0
        yield 'mvtec_acquired_development',a['id'],a['label'],p,truth,m
    normals=sorted((R/'validation/normal_rgb').glob('calib_*.png'))
    if len(normals)!=230:raise ValueError('Expected 230 historical HDMI-acquired normal calibration images')
    for p in normals:
        yield 'mvtec_acquired_normal_calibration',p.stem,'good',p,np.zeros((720,1280),bool),None
    for a in json.loads((R/'data/independent_mcs2/manifest.json').read_text())['items']:
        m=R/'data/independent_mcs2/truth'/f"holdout_{a['index']:03d}.png"
        with Image.open(m) as im:truth=np.asarray(im.convert('L'))>0
        yield 'mcs2_source_development',str(a['index']),'crack',R/'data/independent_mcs2/hdmi'/f"holdout_{a['index']:03d}.png",truth,m


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    if args.out.exists():raise FileExistsError('Do not overwrite previous experiments')
    args.out.mkdir(parents=True)
    rows=[];sources=[];started=time.time()
    variants={'baseline':(False,False,24),'ridge24_seeds_only':(True,False,24),
              'ridge24':(True,True,24),'ridge32':(True,True,32),
              'ridge40':(True,True,40)}
    for i,(ds,sid,label,p,truth,m) in enumerate(cohort()):
        rgb=load(p);a=rgb.astype(np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
        keep=np.zeros(gray.shape,bool);keep[80:640,80:1200]=True
        scores=(valley(gray,8),valley(gray,16),ridge_score(gray))
        if rgb.shape!=(720,1280,3) or truth.shape!=(720,1280):raise ValueError('Unexpected source raster')
        sources.append(dict(dataset=ds,id=sid,image=p.relative_to(R).as_posix(),sha256=sha(p),mask_sha256=sha(m) if m else None))
        for name,(seeds,weak,threshold) in variants.items():
            mask=mask_from_scores(*scores,keep,ridge_high=threshold,add_seeds=seeds,add_weak=weak)
            rr=regions(mask)
            covered=np.zeros_like(mask)
            for x0,y0,x1,y1 in rr['boxes']:covered[y0:y1+1,x0:x1+1]=True
            rows.append(dict(dataset=ds,id=sid,label=label,variant=name,alarm=bool(rr['boxes'] or rr['overflow']),
                tp=int((mask&truth).sum()),fp=int((mask&~truth).sum()),fn=int((~mask&truth).sum()),
                box_truth=int((covered&truth).sum()),truth_pixels=int(truth.sum()),boxes=rr['boxes'],overflow=rr['overflow']))
        if i%20==0:
            print(json.dumps(dict(images=i+1,elapsed_s=round(time.time()-started,1))),flush=True)
    summary=[]
    for ds in sorted({r['dataset'] for r in rows}):
        for name in variants:
            group=[r for r in rows if r['dataset']==ds and r['variant']==name]
            tp=sum(r['tp'] for r in group);fp=sum(r['fp'] for r in group);fn=sum(r['fn'] for r in group)
            summary.append(dict(dataset=ds,variant=name,images=len(group),
                crack_images=sum(r['label']=='crack' for r in group),normal_images=sum(r['label']=='good' for r in group),
                crack_alarms=sum(r['label']=='crack' and r['alarm'] for r in group),normal_alarms=sum(r['label']=='good' and r['alarm'] for r in group),
                pixel_recall=tp/(tp+fn) if tp+fn else None,pixel_precision=tp/(tp+fp) if tp+fp else None,
                box_truth_coverage=sum(r['box_truth'] for r in group)/(tp+fn) if tp+fn else None,tp=tp,fp=fp,fn=fn))
    proof=dict(scope='OFFLINE FULL-RASTER DEVELOPMENT ABLATION; no independent industrial accuracy or new board test',
        hardware_changed=False,variants=variants,source_sha256={str(p.relative_to(R)):sha(p) for p in [Path(__file__),R/'models/ridge_reference.py',R/'models/valley_reference.py',R/'models/weak_reference.py',R/'models/regions_reference.py']},
        environment=dict(python=sys.version,numpy=np.__version__,platform=platform.platform()),elapsed_s=time.time()-started,
        summary=summary,sources=sources,rows=rows)
    (args.out/'summary.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
