import json,sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,'D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53/tools/reference_tile')
import reference_tile as b,reference_v166 as v
root=Path(__file__).parent/'audit01';rows=json.loads((root/'summary.json').read_text())['rows'];result=[]
for row in rows:
 if row['status']!='COMPARED':continue
 d=root/row['id'];reference=b.read_frame(d/'reference.png');aligned=np.array(Image.open(d/'aligned.png'));ref,_=b.matched_reference(reference,row['registration']['dx'],row['registration']['dy'],v.policy());fit=row['photometric'];edge=b.edge_tolerance(reference,v.policy());ep=np.pad(edge,1,mode='edge');edge=np.maximum.reduce([ep[j:j+500,i:i+500] for j in range(3) for i in range(3)])
 norm,_,_,_=b.integer_difference(ref,aligned,fit['gain_q8'],fit['offset_integer'],edge);truth=np.array(Image.open(d/'truth.png'))>0
 score,_,_=v.window_metric(ref,norm,edge)
 for divisor in (2,4):
  e=edge//divisor;strong=score.astype(int)>18+e;weak=score.astype(int)>9+(e>>1);m,regions=b.components(weak,strong,v.policy());tp=int((m&truth).sum());alarm=bool(regions)
  r=dict(id=row['id'],group=row['group'],divisor=divisor,alarm=alarm,tp=tp,coverage=tp/int(truth.sum()) if truth.any() else None);result.append(r)
Path(__file__).with_name('probe_edge_uncertainty.json').write_text(json.dumps(result,indent=2))
for divisor in (2,4):
 s=[r for r in result if r['divisor']==divisor];print(divisor,'normal alarms',[r['id'] for r in s if 'NORMAL' in r['group'] and r['alarm']],'miss',[r['id'] for r in s if r['coverage']==0], 'mincoverage',min(r['coverage'] for r in s if r['coverage'] is not None))
