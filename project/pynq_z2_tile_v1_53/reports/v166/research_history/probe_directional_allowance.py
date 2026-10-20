import json,sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,'D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53/tools/reference_tile')
import reference_tile as b,reference_v166 as v
root=Path(__file__).parent/'audit01';rows=json.loads((root/'summary.json').read_text())['rows'];result=[]
def chroma(a):
 r,g,bb=np.moveaxis(a.astype(np.int16),-1,0)
 return np.stack([(r-bb+256)>>1,(-r+2*g-bb+512)>>2],axis=-1)
for row in rows:
 if row['status']!='COMPARED':continue
 d=root/row['id'];reference=b.read_frame(d/'reference.png');aligned=np.array(Image.open(d/'aligned.png'));ref,_=b.matched_reference(reference,row['registration']['dx'],row['registration']['dy'],v.policy());fit=row['photometric'];edge=b.edge_tolerance(reference,v.policy());ep=np.pad(edge,1,mode='edge');edge=np.maximum.reduce([ep[j:j+500,i:i+500] for j in range(3) for i in range(3)])
 norm,_,_,_=b.integer_difference(ref,aligned,fit['gain_q8'],fit['offset_integer'],edge);truth=np.array(Image.open(d/'truth.png'))>0
 rc=chroma(ref);cc=chroma(norm);pp=np.pad(rc,((2,2),(2,2),(0,0)),mode='edge');lo=np.full_like(rc,255);hi=np.zeros_like(rc)
 for j in range(5):
  for i in range(5):
   vv=pp[j:j+500,i:i+500];lo=np.minimum(lo,vv);hi=np.maximum(hi,vv)
 excess=np.maximum(np.maximum(cc-hi,lo-cc),0).max(-1)
 score=np.maximum(np.abs(v.features(ref).astype(np.int16)-v.features(norm).astype(np.int16)).max(-1),excess)
 # Low chroma variation means a natural/neutral intensity texture. The 1/16
 # RGB-range allowance follows the quantized translation resolution.
 e=np.where((hi-lo).max(-1)<=8,edge//4,edge)
 strong=score>18+e;weak=score>9+(e>>1);m,regions=b.components(weak,strong,v.policy());tp=int((m&truth).sum());alarm=bool(regions)
 result.append(dict(id=row['id'],group=row['group'],alarm=alarm,tp=tp,coverage=tp/int(truth.sum()) if truth.any() else None))
Path(__file__).with_name('probe_directional_allowance.json').write_text(json.dumps(result,indent=2))
print('normal alarms',[r['id'] for r in result if 'NORMAL' in r['group'] and r['alarm']]);print('miss',[r['id'] for r in result if r['coverage']==0]);print('lowest',sorted([r for r in result if r['coverage'] is not None],key=lambda r:r['coverage'])[:6])
