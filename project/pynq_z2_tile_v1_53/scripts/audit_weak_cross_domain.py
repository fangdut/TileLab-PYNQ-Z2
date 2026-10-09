"""Frozen-rule stress audit; no threshold selection and no live PC detector."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from PIL import Image,ImageOps
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_5';sys.path.insert(0,str(R/'models'))
from weak_reference import detect
from regions_reference import regions
prior=json.loads((B/'reports/v15/benchmark/results.json').read_text())
rows=[]
for i,s in enumerate(prior['items']):
 if s['dataset']=='facade_ceramic':continue
 p=Path(s['source_image'])
 if not p.exists():raise FileNotFoundError('Dataset was removed; original files are required: '+str(p))
 assert hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256']
 photo=ImageOps.exif_transpose(Image.open(p)).convert('RGB');photo.thumbnail((500,500),Image.Resampling.BILINEAR)
 im=Image.new('RGB',(1280,720),(30,39,44));im.paste(photo,((1280-photo.width)//2,(720-photo.height)//2))
 mask,_=detect(im,threshold=105);rr=regions(mask)
 rows.append(dict(dataset=s['dataset'],id=s['id'],label=s['label'],baseline_alarm=s['predictions']['calibrated']['alarm'],weak_alarm=bool(rr['boxes'] or rr['overflow']),pixels=int(mask.sum())))
 if len(rows)%200==0:print('Frozen cross-domain audit',len(rows),flush=True)
summary={}
for dataset in sorted({r['dataset'] for r in rows}):
 group=[r for r in rows if r['dataset']==dataset]
 summary[dataset]={label:dict(images=sum(r['label']==label for r in group),old_alarms=sum(r['label']==label and r['baseline_alarm'] for r in group),new_alarms=sum(r['label']==label and r['weak_alarm'] for r in group)) for label in sorted({r['label'] for r in group})}
(R/'reports/weak_crack/cross_domain.json').write_text(json.dumps(dict(scope='OFFLINE ONLY: source-space high threshold 105 retained from V1.5 normal calibration; current HDMI profile 89 is not used on raw files. Roof defects also include shape defects; these are stress data, not a crack-accuracy estimate.',summary=summary,items=rows),indent=2))
print(json.dumps(summary),flush=True)
