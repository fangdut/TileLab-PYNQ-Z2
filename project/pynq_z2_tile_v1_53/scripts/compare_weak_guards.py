from pathlib import Path
import json,sys
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_5';sys.path.insert(0,str(R/'models'))
from valley_reference import valley
from weak_reference import grow
from regions_reference import regions
configs=[(89,67,2),(89,67,3),(89,45,2),(89,45,3),(94,71,1),(94,47,1),(98,74,1),(98,49,1)]
items=json.loads((B/'data/real_tiles/hdmi_manifest.json').read_text())['items'];source={s['id']:s for s in json.loads((B/'data/real_tiles/manifest.json').read_text())['samples']}
jobs=[dict(id=f'train_{n}',path=B/f'reports/v15/hdmi_calibration/calib_{n:03d}.png',label='train_good') for n in range(230)]
for i in items:
 if i['label'] in ('crack','good'):jobs.append(dict(id=i['id'],path=B/f"reports/v15/real_board/real_{i['index']:03d}_original.png",label=i['label'],mask=source[i['id']].get('mask')))
tot={str(c):dict(train_good=0,good=0,crack=0,tp=0,fp=0,fn=0) for c in configs};rows=[]
for k,j in enumerate(jobs):
 a=np.asarray(Image.open(j['path']).convert('RGB'),dtype=np.int32);s=valley((77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8)
 keep=np.zeros(s.shape,bool);keep[80:640,80:1200]=1;gt=np.zeros_like(keep)
 if j.get('mask'):gt[110:610,390:890]=np.asarray(Image.open(B/'data/real_tiles'/j['mask']).convert('L').resize((500,500),Image.Resampling.NEAREST))>0
 row=dict(id=j['id'],label=j['label'],results={})
 for c in configs:
  hi,lo,neighbors=c;m=(s>hi)&keep;weak=(s>lo)&keep
  for _ in range(2):m=grow(m,weak,neighbors)
  rr=regions(m);alarm=bool(rr['boxes'] or rr['overflow']);v=tot[str(c)];v[j['label']]+=alarm;row['results'][str(c)]=alarm
  if j['label']=='crack':
   for key,mask in [('tp',m&gt),('fp',m&~gt),('fn',~m&gt)]:v[key]+=int(mask.sum())
 rows.append(row)
 if(k+1)%50==0:print('Guard checks',k+1,flush=True)
for v in tot.values():v.update(recall=v['tp']/(v['tp']+v['fn']),precision=v['tp']/(v['tp']+v['fp']))
(R/'reports/weak_crack/guard_comparison.json').write_text(json.dumps(dict(scope='Historical exploration; test labels used to compare architectures, not an independent benchmark',summary=tot,items=rows),indent=2))
print(json.dumps(tot),flush=True)
