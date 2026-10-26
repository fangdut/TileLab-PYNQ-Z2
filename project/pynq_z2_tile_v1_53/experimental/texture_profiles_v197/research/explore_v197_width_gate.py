"""Development ablation: narrow print line response vs broad natural veins."""
from pathlib import Path
import sys,json,numpy as np
from PIL import Image
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');O=W/'v197_width01';O.mkdir(exist_ok=False)
sys.path.insert(0,str(P/'experimental/texture_profiles_v197'));from reference import sample_rgb,extract
model=json.loads((W/'v197_new80_01/frozen_model.json').read_text())['model'];rep=np.array(model['representatives'])
def features(r):
    y=sample_rgb(Image.open(Path(r['base'])/r['file']).convert('RGB'));stats=extract(y);group=int(np.abs(rep-stats['descriptor']).sum(1).argmin())
    n1=np.abs((2*y[:,1:-1]-y[:,:-2]-y[:,2:]).sum(0));n1=np.pad(n1,(1,1));neighbor=np.maximum.reduce([n1,np.r_[n1[0],n1[:-1]],np.r_[n1[1:],n1[-1]]])
    scores={k:[] for k in ['ungated','narrow2','narrow1']}
    for i,d in enumerate([2,4,8]):
        n=np.abs(stats['signed'][i]);e=stats['absolute'][i];v=n*n//(e+1);base=neighbor[d:256-d]
        scores['ungated'].append(v);scores['narrow2'].append(np.where(2*base>=n,v,0));scores['narrow1'].append(np.where(base>=n,v,0))
    return dict(id=r['id'],label=r['label'],group=group,values=scores)
normal=json.loads((W/'v197_expanded01/normal_manifest.json').read_text());cal=[features(r) for r in normal if r['role']=='calibration']
tests=[]
for name in ['v196_dataset_hfe01','v196_hfe_holdout01','v197_new80_01']:
    rr=json.loads((W/name/'manifest.json').read_text())['images'];tests += [dict(r,base=str(W/name)) for r in rr if r.get('role','test')=='test']
thresholds={}
for grouping in ['global','group']:
    thresholds[grouping]={}
    for g in range(8 if grouping=='group' else 1):
        cc=[r for r in cal if grouping=='global' or r['group']==g]
        thresholds[grouping][g]={key:[max(int(r['values'][key][i].max()) for r in cc)+1 for i in range(3)] for key in ['ungated','narrow2','narrow1']}
(O/'frozen_normal_thresholds.json').write_text(json.dumps(dict(thresholds=thresholds,normal_calibration=len(cal),scope='NORMAL_ONLY_RULES_ALL160_TESTS_NOW_EXPOSED'),indent=2),encoding='utf8')
tt=[features(r) for r in tests];summaries={};records=[]
for grouping in thresholds:
    for key in ['ungated','narrow2','narrow1']:
        rows=[]
        for r in tt:
            g=r['group'] if grouping=='group' else 0;t=thresholds[grouping][g][key];a=any(bool((v>limit).any()) for v,limit in zip(r['values'][key],t))
            rows.append(dict(id=r['id'],label=r['label'],alarm=a,group=r['group']))
        tp=sum(r['label']=='defect' and r['alarm'] for r in rows);fp=sum(r['label']=='good' and r['alarm'] for r in rows)
        summaries[grouping+'_'+key]=dict(tp=tp,fp=fp,tn=80-fp,fn=80-tp);records.append(dict(candidate=grouping+'_'+key,results=rows))
(O/'summary.json').write_text(json.dumps(dict(scope='EXPOSED160_OFFLINE_DEVELOPMENT',metrics=summaries),indent=2),encoding='utf8');(O/'results.json').write_text(json.dumps(records,indent=2),encoding='utf8');print(json.dumps(summaries))
