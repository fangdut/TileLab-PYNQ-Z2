"""Normal-only grouping feasibility. Offline development, not deployed vision."""
from pathlib import Path
import json,hashlib,numpy as np
from PIL import Image
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');D=W/'v196_dataset_hfe01';O=W/'v197_profiles01';O.mkdir(exist_ok=False)
rows=json.loads((D/'manifest.json').read_text())['images'];new=json.loads((W/'v196_hfe_holdout01/manifest.json').read_text())['images']
def features(row,base):
    rgb=np.asarray(Image.open(base/row['file']).convert('RGB'),dtype=np.int64);h,w=rgb.shape[:2]
    yy=np.clip((2*np.arange(224)+1)*h-224,0,(h-1)*448)//448;y=((rgb[:,:,0]+2*rgb[:,:,1]+rgb[:,:,2])//4)[yy]
    hist=np.bincount((y//16).ravel(),minlength=16)*256//y.size
    weighted=[];ratio=[];count=[];energy=[]
    for d in [2,4,8]:
        r=2*y[:,d:w-d]-y[:,:w-2*d]-y[:,2*d:];n=np.abs(r.sum(0));e=np.abs(r).sum(0)
        weighted.append(n*n//(e+1));ratio.append(np.where(e>=448,n*256//(e+1),0))
        count.append(np.maximum((r>2).sum(0),(r<-2).sum(0)));energy.append(int(np.abs(r).sum()//r.size))
    return dict(id=row['id'],label=row['label'],desc=np.r_[hist,np.asarray(energy)*4],weighted=np.stack(weighted,axis=0) if False else weighted,ratio=ratio,count=count)
allrows=[features(r,D) for r in rows]+[features(r,W/'v196_hfe_holdout01') for r in new]
byid={r['id']:r for r in allrows};memory=[byid[r['id']] for r in rows if r['role']=='memory'];cal=[byid[r['id']] for r in rows if r['role']=='calibration'];tests=[dict(byid[r['id']],set='original40') for r in rows if r['role']=='test']+[dict(byid[r['id']],set='opened40') for r in new]
def maxima(items,key):return np.asarray([[int(v.max()) for v in r[key]] for r in items],dtype='int64')
def thresholds(items):return {key:maxima(items,key).max(0)+1 for key in ['weighted','ratio','count']}
def alarm(row,t,mode):
    flags=[]
    for i in range(3):
        w=row['weighted'][i]>t['weighted'][i];r=row['ratio'][i]>t['ratio'][i];c=row['count'][i]>t['count'][i]
        flags.append(w if mode=='weighted' else r if mode=='ratio' else w&r if mode=='and_ratio' else w&c)
    return any(v.any() for v in flags)
models=[]
global_t=thresholds(cal)
models.append(dict(name='global',k=0,reps=None,cal=cal,thresholds=global_t))
for k in [4,8,10]:
    x=np.stack([r['desc'] for r in memory]);near=np.full(len(x),2**62,dtype='int64');idx=0;chosen=[]
    for _ in range(k):
        chosen.append(idx);near=np.minimum(near,((x-x[idx])**2).sum(1));idx=int(near.argmax())
    rep=x[chosen].copy()
    for _ in range(40):
        assignment=((x[:,None,:]-rep[None,:,:])**2).sum(2).argmin(1);updated=rep.copy()
        for g in range(k):
            m=x[assignment==g]
            if len(m):updated[g]=(m.sum(0)+len(m)//2)//len(m)
        if np.array_equal(updated,rep):break
        rep=updated
    def group(r):return int(((rep-r['desc'])**2).sum(1).argmin())
    groups={g:[r for r in cal if group(r)==g] for g in range(k)}
    models.append(dict(name='group'+str(k),k=k,reps=rep,cal=groups,thresholds={g:thresholds(v) for g,v in groups.items() if len(v)>=4}))
records=[];summaries={}
for model in models:
    for mode in ['weighted','ratio','and_ratio','and_count']:
        name=model['name']+'_'+mode;actual=[]
        for row in tests:
            g=int(((model['reps']-row['desc'])**2).sum(1).argmin()) if model['k'] else 0
            t=model['thresholds'].get(g) if model['k'] else model['thresholds']
            decision=bool(alarm(row,t,mode)) if t is not None else None
            actual.append(dict(id=row['id'],label=row['label'],set=row['set'],group=g,alarm=decision))
        results={}
        for subset in ['original40','opened40','all80']:
            rr=[r for r in actual if r['set']==subset or subset=='all80']
            results[subset]={key:sum(1 for r in rr if predicate(r)) for key,predicate in dict(tp=lambda r:r['label']=='defect' and r['alarm'] is True,fp=lambda r:r['label']=='good' and r['alarm'] is True,tn=lambda r:r['label']=='good' and r['alarm'] is False,fn=lambda r:r['label']=='defect' and r['alarm'] is False,unknown_good=lambda r:r['label']=='good' and r['alarm'] is None,unknown_defect=lambda r:r['label']=='defect' and r['alarm'] is None).items()}
        summaries[name]=results;records.append(dict(candidate=name,results=actual))
freeze=[]
for m in models:
    freeze.append(dict(name=m['name'],representatives=m['reps'].tolist() if m['k'] else None,cal_counts={str(k):len(v) for k,v in m['cal'].items()} if m['k'] else len(cal),thresholds={str(g):{k:v.tolist() for k,v in t.items()} for g,t in m['thresholds'].items()} if m['k'] else {k:v.tolist() for k,v in m['thresholds'].items()}))
(O/'models.json').write_text(json.dumps(dict(models=freeze,minimum_calibration=4,group_ground_truth=False,scope='NORMAL_ONLY_DESCRIPTOR_GROUPS_NOT_FLOWER_IDS'),indent=2),encoding='utf8')
(O/'results.json').write_text(json.dumps(records,indent=2),encoding='utf8');(O/'summary.json').write_text(json.dumps(dict(scope='EXPOSED_DEVELOPMENT_OFFLINE_NOT_BOARD',metrics=summaries),indent=2),encoding='utf8')
print(json.dumps(summaries))
