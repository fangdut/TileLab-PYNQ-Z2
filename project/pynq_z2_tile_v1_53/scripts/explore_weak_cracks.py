"""Historical regression exploration. Reads V1.5 evidence; never changes it."""
from pathlib import Path
import json,sys
import numpy as np
from PIL import Image
def expand(mask):
 padded=np.pad(mask,1);out=np.zeros_like(mask)
 for y in range(3):
  for x in range(3):out|=padded[y:y+mask.shape[0],x:x+mask.shape[1]]
 return out
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_5'
sys.path.insert(0,str(R/'models'))
from valley_reference import valley
from regions_reference import regions
items=json.loads((B/'data/real_tiles/hdmi_manifest.json').read_text())['items']
source={s['id']:s for s in json.loads((B/'data/real_tiles/manifest.json').read_text())['samples']}
variants=[('baseline',89,89,0),('grow2_75',89,67,2),('grow2_50',89,45,2),('grow4_75',89,67,4)]
rows=[]
for item in items:
 if item['label'] not in ('good','crack'):continue
 n=item['index'];p=B/f'reports/v15/real_board/real_{n:03d}_original.png'
 a=np.asarray(Image.open(p).convert('RGB'),dtype=np.int32)
 score=valley((77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8)
 roi=np.zeros(score.shape,bool);roi[80:640,80:1200]=True
 gt=np.zeros_like(roi);s=source[item['id']]
 if s.get('mask'):gt[110:610,390:890]=np.asarray(Image.open(B/'data/real_tiles'/s['mask']).convert('L').resize((500,500),Image.Resampling.NEAREST))>0
 row=dict(id=item['id'],index=n,label=item['label'],variants={})
 for name,high,low,steps in variants:
  mask=(score>high)&roi;weak=(score>low)&roi
  for _ in range(steps):mask=expand(mask)&weak
  rr=regions(mask);tp=int((mask&gt).sum());fp=int((mask&~gt).sum());fn=int((~mask&gt).sum())
  row['variants'][name]=dict(alarm=bool(rr['boxes'] or rr['overflow']),pixels=int(mask.sum()),tp=tp,fp=fp,fn=fn,boxes=rr['boxes'])
 rows.append(row)
summary={}
for name,*_ in variants:
 crack=[r['variants'][name] for r in rows if r['label']=='crack'];good=[r['variants'][name] for r in rows if r['label']=='good']
 tp=sum(r['tp'] for r in crack);fp=sum(r['fp'] for r in crack);fn=sum(r['fn'] for r in crack)
 summary[name]=dict(crack_alarms=sum(r['alarm'] for r in crack),good_alarms=sum(r['alarm'] for r in good),recall=tp/(tp+fn),precision=tp/(tp+fp),iou=tp/(tp+fp+fn),missed=[r['id'] for r in rows if r['label']=='crack' and not r['variants'][name]['alarm']])
(R/'reports/weak_crack/exploration.json').write_text(json.dumps(dict(scope='Historical 50 captured images; architecture exploration, NOT blind validation',variants=variants,summary=summary,items=rows),indent=2))
print(json.dumps(summary),flush=True)
