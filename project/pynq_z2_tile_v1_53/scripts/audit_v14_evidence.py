"""Audit saved FPGA evidence against source barcodes (validation only)."""
from pathlib import Path
import json,sys,io
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
from board_v14_continuous import barcode
T=R/'reports/v14';videos=json.loads((R/'data/conveyor/continuous_timeline.json').read_text())['videos']
all_rows=[];best_written=False
for mode,seconds in [('video',60),('fast',60),('ultrafast',300),('ultrafast',60)]:
 p=T/f'continuous/{mode}_{seconds}s.json'
 if not p.exists():continue
 test=json.loads(p.read_text());timeline=next(v['timeline'] for v in videos if v['name']==mode)
 for event in test['events']:
  path=R/'review_records'/(event['key']+'.png');raw=path.read_bytes();code=barcode(raw)
  visible=timeline[code]['visible'];center=[v for v in visible if v['x']<=640<v['x']+560]
  row=dict(test=p.name,key=event['key'],product_id=event['product_id'],barcode=code,center_product=center,
           source_crack=bool(len(center)==1 and center[0]['crack']),fully_in_roi=bool(len(center)==1 and center[0]['x']>80 and center[0]['x']+559<1199))
  all_rows.append(row)
  if mode=='ultrafast' and row['source_crack'] and row['fully_in_roi'] and not best_written:
   im=Image.open(io.BytesIO(raw)).convert('RGB');d=ImageDraw.Draw(im)
   for b in event['boxes']:d.rectangle(tuple(b),outline=(255,40,40),width=3)
   im.save(T/'best_product_example.png')
   # Keep the first full-speed example; never modify the original evidence.
   (T/'best_product_example.json').write_text(json.dumps(dict(row=row,event=event),indent=2));best_written=True
result=dict(samples=len(all_rows),all_source_crack=all(r['source_crack'] for r in all_rows),all_fully_in_roi=all(r['fully_in_roi'] for r in all_rows),rows=all_rows)
(T/'saved_evidence_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
assert all_rows and result['all_source_crack'] and result['all_fully_in_roi']
