"""Portable source-image evaluation. Reserved data require a frozen profile."""
from pathlib import Path
import argparse,datetime,hashlib,json,sys,time
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'models'),str(R/'scripts')]
from evaluate_ridge_v154 import cohort
from support_profiles_v155 import compute_features,mask_from_features,PROFILES
from regions_reference import regions
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def source_cohort(split):
    for source in ['hfenet','visuceram']:
        data=json.loads((R/f'data/v155_research/{source}_manifest.json').read_text())
        for item in data['selected']:
            if item['split']!=split:continue
            p=R/item['local_image'];lab=R/item['local_label'];rgb=np.zeros((720,1280,3),np.uint8)
            if sha(p)!=item['sha256']:raise ValueError('New-source image hash changed')
            with Image.open(p) as im:
                if source=='hfenet':rgb[232:488,80:1200]=np.asarray(im.rotate(-90,expand=True).convert('RGB'))[:,144:1264]
                else:rgb[110:610,390:890]=np.asarray(im.convert('RGB'))
            boxes=[];invalid=0;contradiction=False
            if source=='hfenet' and item['class_name']=='normal':
                with Image.open(lab) as im:
                    if np.asarray(im).any():raise ValueError('Nonempty truth in a normal source image')
            if source=='visuceram':
                for row in lab.read_text().splitlines():
                    cid,cx,cy,w,h=map(float,row.split())
                    if int(cid) not in (0,2):continue
                    if item['class_name']=='normal':contradiction=True
                    if not (0<=cx-w/2<cx+w/2<=1 and 0<=cy-h/2<cy+h/2<=1):invalid+=1;continue
                    boxes.append([390+(cx-w/2)*500,110+(cy-h/2)*500,390+(cx+w/2)*500-1,110+(cy+h/2)*500-1])
            yield dict(dataset=source+'_'+split,id=item['sha256'][:16],label=item['class_name'],rgb=rgb,image=p,mask=lab,
                       truth=None,truth_boxes=boxes,invalid_truth_boxes=invalid,label_contradiction=contradiction)
def old_cohort():
    for ds,sid,label,p,truth,m in cohort():
        with Image.open(p) as im:rgb=np.asarray(im.convert('RGB'))
        yield dict(dataset=ds,id=sid,label=label,rgb=rgb,image=p,mask=m,truth=truth,truth_boxes=[],invalid_truth_boxes=0,label_contradiction=False)
def iou(a,b):
    l=max(a[0],b[0]);t=max(a[1],b[1]);r=min(a[2],b[2]);bt=min(a[3],b[3]);inter=max(0,r-l+1)*max(0,bt-t+1)
    return inter/((a[2]-a[0]+1)*(a[3]-a[1]+1)+(b[2]-b[0]+1)*(b[3]-b[1]+1)-inter)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--profile',type=Path,required=True);ap.add_argument('--cohort',choices=['old','development','reserved'],required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    profile=json.loads(args.profile.read_text());before=sha(args.profile)
    if profile.get('selection_frozen') is not True:raise ValueError('Freeze selection before canonical evaluation')
    if profile['profiles']!=PROFILES:raise ValueError('Frozen and implemented profiles differ')
    hashes=json.loads((R/'data/v155_research/FILE_HASHES.json').read_text())
    args.out.mkdir(parents=True,exist_ok=False);start=time.time();rows=[];sources=[]
    snapshot=args.out/'source';snapshot.mkdir()
    paths=[Path(__file__)]+[R/'models'/n for n in ['support_profiles_v155.py','ridge_reference.py','valley_reference.py','weak_reference.py','regions_reference.py']]
    for rel,digest in profile['source_sha256'].items():
        if sha(R/rel)!=digest:raise ValueError('Frozen model source changed')
    for p in paths:(snapshot/p.name).write_bytes(p.read_bytes())
    declaration=dict(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='OFFLINE SOURCE/ACQUIRED RGB evaluation; new candidate is not board-accepted; no factory validation',cohort=args.cohort,
                     profile=profile,profile_sha256=before,source_sha256={p.relative_to(R).as_posix():sha(p) for p in paths},physical_product_independence=False)
    (args.out/'declaration.json').write_text(json.dumps(declaration,indent=2))
    items=old_cohort() if args.cohort=='old' else source_cohort(args.cohort)
    for i,item in enumerate(items):
        rgb=item.pop('rgb');truth=item.pop('truth');a=rgb.astype(np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
        keep=np.zeros(gray.shape,bool);keep[80:640,80:1200]=True
        if args.cohort!='old':
            for p in [item['image'],item['mask']]:
                if sha(p)!=hashes[p.relative_to(R).as_posix()]:raise ValueError('Frozen source/label changed')
        features=compute_features(gray)
        sources.append(dict(dataset=item['dataset'],id=item['id'],image=item['image'].relative_to(R).as_posix(),image_sha256=sha(item['image']),label_sha256=sha(item['mask']) if item['mask'] else None))
        for variant in PROFILES:
            mask=mask_from_features(features,keep,variant);rr=regions(mask)
            rows.append(dict(dataset=item['dataset'],id=item['id'],label=item['label'],variant=variant,alarm=bool(rr['boxes'] or rr['overflow']),
                             pixels=int(mask.sum()),boxes=rr['boxes'],areas=rr['areas'],overflow=rr['overflow'],
                             tp=int((mask&truth).sum()) if truth is not None else None,fp=int((mask&~truth).sum()) if truth is not None else None,fn=int((~mask&truth).sum()) if truth is not None else None,
                             box_hit_iou025=any(iou(x,y)>=.25 for x in item['truth_boxes'] for y in rr['boxes']),box_hit_iou050=any(iou(x,y)>=.5 for x in item['truth_boxes'] for y in rr['boxes']),
                             invalid_truth_boxes=item['invalid_truth_boxes'],label_contradiction=item['label_contradiction'],mask_sha256=hashlib.sha256(np.packbits(mask.ravel(),bitorder='little').tobytes()).hexdigest()))
        if i%40==0:print(json.dumps(dict(images=i+1,seconds=round(time.time()-start,1))),flush=True)
    if sha(args.profile)!=before:raise ValueError('Frozen profile changed during evaluation')
    summary=[]
    for ds in sorted({r['dataset'] for r in rows}):
        for variant in PROFILES:
            g=[r for r in rows if r['dataset']==ds and r['variant']==variant];pixel=[r for r in g if r['tp'] is not None];tp=sum(r['tp'] for r in pixel);fp=sum(r['fp'] for r in pixel);fn=sum(r['fn'] for r in pixel)
            groups={cls:dict(images=sum(r['label']==cls and not r['label_contradiction'] for r in g),alarms=sum(r['label']==cls and r['alarm'] and not r['label_contradiction'] for r in g),box_hits025=sum(r['label']==cls and r['box_hit_iou025'] for r in g),box_hits050=sum(r['label']==cls and r['box_hit_iou050'] for r in g)) for cls in sorted({r['label'] for r in g})}
            summary.append(dict(dataset=ds,variant=variant,images=len(g),groups=groups,tp=tp if pixel else None,fp=fp if pixel else None,fn=fn if pixel else None,
                                recall=tp/(tp+fn) if tp+fn else None,precision=tp/(tp+fp) if tp+fp else None,label_contradictions=sum(r['label_contradiction'] for r in g)))
    result=dict(**declaration,summary=summary,sources=sources,rows=rows,seconds=time.time()-start,new_board_acceptance=False,industrial_validation=False)
    (args.out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
