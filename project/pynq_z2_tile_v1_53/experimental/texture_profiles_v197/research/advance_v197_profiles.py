"""Expanded good-only calibration. No fresh validation images opened here."""
from pathlib import Path
import io,json,hashlib,zipfile,datetime,numpy as np
from PIL import Image
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');O=W/'v197_expanded01';O.mkdir(exist_ok=False)
old=json.loads((W/'v196_dataset_hfe01/manifest.json').read_text())['images'];extra=json.loads((W/'v196_hfe_holdout01/manifest.json').read_text())['images']
sha=lambda b:hashlib.sha256(b).hexdigest();z=zipfile.ZipFile(W/'v196_hfenet01/HFENet_Dataset.zip')
used={r['original_rgb_sha256'] for r in old+extra};manifest=[]
for r in old:
    if r['role']!='test':manifest.append(dict(r,base=str(W/'v196_dataset_hfe01')))
paths=sorted([p for p in z.namelist() if '/train/no_defective/img/' in p and p.endswith('.bmp')],key=lambda p:sha(('v197-normal-extension|'+p).encode()))
normals=O/'prepared';normals.mkdir()
added=0
for path in paths:
    raw=z.read(path);rgb=np.asarray(Image.open(io.BytesIO(raw)).convert('RGB'));rs=sha(rgb.tobytes())
    if rs in used:continue
    mask_path=path.replace('/img/','/lab/').rsplit('.',1)[0]+'_label.bmp';gt=np.asarray(Image.open(io.BytesIO(z.read(mask_path))).convert('L'))>1
    assert not gt.any();assert rgb.shape==(1408,256,3)
    used.add(rs);ident=sha(('HFENet|'+path).encode())[:24];y=704*(int(sha(('v196-hfe-view|'+path).encode())[:8],16)%2)
    file=normals/(ident+'.png');Image.fromarray(rgb[y:y+704]).save(file)
    manifest.append(dict(id=ident,archive_path=path,original_sha256=sha(raw),original_rgb_sha256=rs,crop=[0,y,256,704],file='prepared/'+file.name,base=str(O),prepared_sha256=sha(file.read_bytes()),role='memory' if added<128 else 'calibration',label='good'))
    added+=1
    if added==384:break
assert added==384
(O/'normal_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
def features(row):
    rgb=np.asarray(Image.open(Path(row['base'])/row['file']).convert('RGB'),dtype='int64');h,w=rgb.shape[:2]
    yy=np.clip((2*np.arange(224)+1)*h-224,0,(h-1)*448)//448;y=((rgb[:,:,0]+2*rgb[:,:,1]+rgb[:,:,2])//4)[yy]
    hist=np.bincount((y//16).ravel(),minlength=16)*256//y.size;values={};energy=[]
    for d in [2,4,8]:
        r=2*y[:,d:w-d]-y[:,:w-2*d]-y[:,2*d:];n=np.abs(r.sum(0));e=np.abs(r).sum(0)
        values[d]=(n*n//(e+1),np.where(e>=448,n*256//(e+1),0));energy.append(int(np.abs(r).sum()//r.size)*4)
    return dict(id=row['id'],label=row['label'],desc=np.r_[hist,energy],weighted=np.array([values[d][0].max() for d in [2,4,8]]),ratio=np.array([values[d][1].max() for d in [2,4,8]]),columns=values)
norm=[dict(features(r),role=r['role']) for r in manifest];memory=[r for r in norm if r['role']=='memory'];cal=[r for r in norm if r['role']=='calibration'];x=np.stack([r['desc'] for r in memory])
models=[]
for distance in ['l2','l1']:
    dist=lambda a:np.abs(a).sum(-1) if distance=='l1' else (a*a).sum(-1)
    near=np.full(len(x),2**62,dtype='int64');idx=0;chosen=[]
    for _ in range(8):chosen.append(idx);near=np.minimum(near,dist(x-x[idx]));idx=int(near.argmax())
    rep=x[chosen].copy()
    for _ in range(40):
        assignment=dist(x[:,None,:]-rep[None,:,:]).argmin(1);updated=rep.copy()
        for g in range(8):
            members=x[assignment==g]
            if len(members):updated[g]=np.median(members,axis=0).astype('i8') if distance=='l1' else (members.sum(0)+len(members)//2)//len(members)
        if np.array_equal(rep,updated):break
        rep=updated
    def group(r):return int(dist(rep-r['desc']).argmin())
    thresholds={};counts={}
    for g in range(8):
        cc=[r for r in cal if group(r)==g];counts[g]=len(cc)
        if len(cc)>=8:thresholds[g]={key:np.stack([r[key] for r in cc]).max(0).tolist() for key in ['weighted','ratio']}
        if g in thresholds:thresholds[g]={key:[v+1 for v in value] for key,value in thresholds[g].items()}
    models.append(dict(name=distance,representatives=rep.tolist(),thresholds=thresholds,cal_counts=counts))
freeze=dict(scope='GOOD_ONLY_TEXTURE_PROFILES_NOT_TRUE_FLOWER_IDS_NOT_BOARD',frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),normal_memory=len(memory),normal_calibration=len(cal),k=8,minimum_calibration=8,models=models)
(O/'frozen.json').write_text(json.dumps(freeze,indent=2),encoding='utf8')
tests=[dict(r,base=str(W/'v196_dataset_hfe01')) for r in old if r['role']=='test']+[dict(r,base=str(W/'v196_hfe_holdout01')) for r in extra]
features_test=[features(r) for r in tests];summaries={};records=[]
for model in models:
    rep=np.array(model['representatives']);name=model['name']
    for mode in ['weighted','ratio','and_ratio']:
        result=[]
        for r in features_test:
            dd=rep-r['desc'];g=int((np.abs(dd).sum(1) if name=='l1' else (dd*dd).sum(1)).argmin());t=model['thresholds'].get(g)
            flags=[]
            if t:
                for i,d in enumerate([2,4,8]):
                    w,ratio=r['columns'][d];a=w>t['weighted'][i];b=ratio>t['ratio'][i]
                    flags.append(a if mode=='weighted' else b if mode=='ratio' else a&b)
            alarm=any(f.any() for f in flags) if t else None
            result.append(dict(id=r['id'],label=r['label'],group=g,alarm=alarm))
        metrics={key:sum(1 for r in result if predicate(r)) for key,predicate in dict(tp=lambda r:r['label']=='defect' and r['alarm'] is True,fp=lambda r:r['label']=='good' and r['alarm'] is True,tn=lambda r:r['label']=='good' and r['alarm'] is False,fn=lambda r:r['label']=='defect' and r['alarm'] is False,unknown_good=lambda r:r['label']=='good' and r['alarm'] is None,unknown_defect=lambda r:r['label']=='defect' and r['alarm'] is None).items()}
        summaries[name+'_'+mode]=metrics;records.append(dict(candidate=name+'_'+mode,results=result))
(O/'development_results.json').write_text(json.dumps(records,indent=2),encoding='utf8');(O/'summary.json').write_text(json.dumps(dict(scope='EXPOSED_80_DEVELOPMENT_ONLY',metrics=summaries),indent=2),encoding='utf8')
print(json.dumps(dict(normal_memory=len(memory),normal_calibration=len(cal),groups=[m['cal_counts'] for m in models],metrics=summaries)))
