"""Frozen HDMI profiles on 800 roof-normal photos, never used for tuning.
Roof ceramic is outside the flat-tile calibration domain. This audits false
alarms after deterministic 500px letterboxing, not factory camera accuracy.
"""
from pathlib import Path
import sys,json,hashlib,time
import numpy as np
from PIL import Image,ImageOps
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_5';sys.path.insert(0,str(R/'models'))
from weak_reference import detect
from regions_reference import regions
O=R/'reports/v132/cross_material';O.mkdir(parents=True,exist_ok=True)
samples=[s for s in json.loads((B/'reports/v15/benchmark/results.json').read_text())['items'] if s['dataset']=='roof_ceramic' and s['label']=='normal']
assert len(samples)==800
declaration=dict(scope=__doc__,before_reading_images=time.time(),profiles=[dict(high=89,passes=2),dict(high=90,passes=4)],threshold_change_allowed=False,images=800)
(O/'declaration.json').write_text(json.dumps(declaration,indent=2));rows=[]
for s in samples:
 p=Path(s['source_image']);assert hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256']
 photo=ImageOps.exif_transpose(Image.open(p)).convert('RGB');photo.thumbnail((500,500),Image.Resampling.BILINEAR)
 im=Image.new('RGB',(1280,720),(30,39,44));im.paste(photo,((1280-photo.width)//2,(720-photo.height)//2))
 row=dict(id=s['id'],source_sha256=s['sha256'])
 for label,t,n in [('legacy',89,2),('quad',90,4)]:
  mask,_=detect(im,threshold=t,passes=n);rr=regions(mask)
  row[label]=dict(alarm=bool(rr['boxes'] or rr['overflow']),pixels=int(mask.sum()),boxes=rr['boxes'])
 rows.append(row)
 if len(rows)%100==0:print('Frozen material stress',len(rows),flush=True)
result=dict(completed=True,scope=__doc__,images=len(rows),normal_alarms={k:sum(r[k]['alarm'] for r in rows) for k in ('legacy','quad')},introduced=sum(not r['legacy']['alarm'] and r['quad']['alarm'] for r in rows),resolved=sum(r['legacy']['alarm'] and not r['quad']['alarm'] for r in rows),rows=rows)
(O/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
