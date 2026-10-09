from pathlib import Path
import json
from board_v18_continuous import barcode
R=Path(__file__).resolve().parents[1];T=R/'reports/v132'
data=json.loads((T/'station_continuous.json').read_text(encoding='utf-8'))
timeline=json.loads((R/'data/real_tiles/video_manifest.json').read_text())['timeline'];period=len(timeline)
obs={r['frame_id']:r['barcode'] for r in data['rows']}
for e in data['records']:obs[e['frame_id']]=barcode((R/'review_records'/(e['id']+'.png')).read_bytes())
cycle=0;previous=None;cycles={};expected=set()
for frame,code in sorted(obs.items()):
 if previous is not None and code<previous-period/2:cycle+=1
 cycles[frame]=cycle;previous=code
 if code<period:
  for tile in timeline[code]['visible']:
   if tile['label']=='crack' and tile['x']<=640<tile['x']+500:expected.add(f"{cycle}:{tile['id']}")
events=[]
for e in data['records']:
 code=obs[e['frame_id']];visible=[t for t in timeline[code]['visible'] if t['x']<=640<t['x']+500] if code<period else []
 assert len(visible)==1,'Evidence does not contain an identifiable central tile'
 tile=visible[0]
 events.append(dict(key=e['id'],physical=f"{cycles[e['frame_id']]}:{tile['id']}",label=tile['label'],center_error=abs(tile['x']+250-640),full=e['selection_full_tile']))
identities=[e['physical'] for e in events];max_error=max(e['center_error'] for e in events)
passed=len(identities)==len(set(identities)) and expected.issubset(set(identities)) and all(e['label']=='crack' and e['full'] for e in events) and max_error<=32
result=dict(passed=passed,physical_products=len(set(identities)),missing=sorted(expected-set(identities)),max_center_error_px=max_error,centering_target_px=32,events=events)
(T/'station_identity_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
assert passed,'Physical source audit did not pass'
