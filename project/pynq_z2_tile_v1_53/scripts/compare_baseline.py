"""Compare old and new candidates using the SAME area/span gate, offline only."""
from pathlib import Path
import sys,json,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'models/baseline_v1_0'))
from evaluate_images import detect as old_detect
from vision_control import Profile
data=json.loads((ROOT/'data/manifest.json').read_text())['items']
rows=[]
for item in data:
    if item['split']!='heldout_synthetic':continue
    rgb=np.asarray(Image.open(ROOT/'data'/item['image']).convert('RGB'))
    mask,info=old_detect(rgb,Profile(dark=1,automatic=1,margin=40,roi=[80,80,1199,639]))
    box=info['bbox'];old=bool(info['count']>=32 and box and max(box[2]-box[0],box[3]-box[1])>=23)
    rows.append(dict(id=item['id'],truth=item['crack'],old_alarm=old,new_alarm=item['alarm']))
summary=[]
for name in ('old_alarm','new_alarm'):
    tp=sum(r['truth'] and r[name] for r in rows);fn=sum(r['truth'] and not r[name] for r in rows)
    fp=sum(not r['truth'] and r[name] for r in rows);tn=sum(not r['truth'] and not r[name] for r in rows)
    summary.append(dict(algorithm=name,tp=tp,fn=fn,fp=fp,tn=tn,recall=tp/(tp+fn),false_alarm_rate=fp/(fp+tn)))
result=dict(provenance='OFFLINE_SYNTHETIC_ONLY',fairness='same area>=32 and max span>=24 gate, same ROI; different candidate extraction',
            old_profile='gray dark I<clamp(mean-40), 3x3 opening; converged auto target only',new_profile='local contrast>12, no morphology',summary=summary,rows=rows)
(ROOT/'reports/old_vs_tile_synthetic.json').write_text(json.dumps(result,indent=2));print(json.dumps(summary))
