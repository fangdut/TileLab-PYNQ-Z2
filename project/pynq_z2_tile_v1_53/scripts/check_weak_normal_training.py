"""Normal-only guard for bounded hysteresis candidates on captured training data."""
from pathlib import Path
import sys,json
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_5';sys.path.insert(0,str(R/'models'))
from valley_reference import valley
from regions_reference import regions
def expand(mask):
 p=np.pad(mask,1);o=np.zeros_like(mask)
 for y in range(3):
  for x in range(3):o|=p[y:y+mask.shape[0],x:x+mask.shape[1]]
 return o
rows=[]
for n in range(230):
 a=np.asarray(Image.open(B/f'reports/v15/hdmi_calibration/calib_{n:03d}.png').convert('RGB'),dtype=np.int32)
 s=valley((77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8);roi=np.zeros(s.shape,bool);roi[80:640,80:1200]=1
 row=dict(index=n)
 for name,lo in [('baseline',89),('grow2_75',67),('grow2_50',45)]:
  m=(s>89)&roi
  if lo!=89:
   w=(s>lo)&roi
   for _ in range(2):m=expand(m)&w
  r=regions(m);row[name]=dict(alarm=bool(r['boxes'] or r['overflow']),pixels=int(m.sum()))
 rows.append(row)
 if (n+1)%50==0:print('Normals',n+1,flush=True)
summary={mode:sum(r[mode]['alarm'] for r in rows) for mode in ('baseline','grow2_75','grow2_50')}
(R/'reports/weak_crack/normal_training.json').write_text(json.dumps(dict(images=230,threshold_high=89,summary=summary,items=rows),indent=2))
print(json.dumps(summary),flush=True)
