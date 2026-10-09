from pathlib import Path
import json,sys
import numpy as np
R=Path(__file__).resolve().parents[1];T=R/'reports/v132';sys.path.insert(0,str(R/'scripts'))
from board_v18_continuous import barcode
real_timeline=json.loads((R/'data/real_tiles/video_manifest.json').read_text())['timeline']
synthetic=json.loads((R/'data/conveyor/continuous_timeline.json').read_text())['videos']
result={}
for mode,seconds in [('ultrafast',60),('real_video',120)]:
 data=json.loads((T/f'continuous/{mode}_{seconds}s.json').read_text());rows=[]
 source_stall=0.0;max_source_stall=0.0;last_code=None
 for sample in data['rows']:
  source_stall=source_stall+sample['interval_ms'] if sample['barcode']==last_code else 0.0
  max_source_stall=max(max_source_stall,source_stall);last_code=sample['barcode']
 timeline=real_timeline if mode=='real_video' else next(v for v in synthetic if v['name']==mode)['timeline'];period=len(timeline);width=500 if mode=='real_video' else 560
 observations={r['frame_id']:r['barcode'] for r in data['rows']}
 for e in data['events']:
  code=barcode((R/'review_records'/(e['key']+'.png')).read_bytes());observations[e['frame_id']]=code
 cycles={};cycle=0;previous=None
 for frame,code in sorted(observations.items()):
  if previous is not None and code<previous-period/2:cycle+=1
  cycles[frame]=cycle;previous=code
 for e in data['events']:
  code=observations[e['frame_id']];truth=None;cx=None;identity=None
  if code<period:
   center=[v for v in timeline[code]['visible'] if v['x']<=640<v['x']+width]
   if len(center)==1:
    tile=center[0];truth=tile['label'] if mode=='real_video' else ('crack' if tile['crack'] else 'good');cx=tile['x']+width/2
    identity=f"{cycles[e['frame_id']]}:{tile['id'] if mode=='real_video' else tile['tile']}"
  rows.append(dict(key=e['key'],product_id=e['product_id'],frame_id=e['frame_id'],code=code,source_cycle=cycles[e['frame_id']],physical_identity=identity,label=truth,center_error_px=abs(cx-640) if cx is not None else None,fpga_center_error_px=e.get('selection_center_error_px'),full=e.get('selection_full_tile',False)))
 physical=[r['physical_identity'] for r in rows if r['physical_identity'] is not None]
 expected_physical=set()
 for frame,code in observations.items():
  if code>=period:continue
  for tile in timeline[code]['visible']:
   is_crack=tile['label']=='crack' if mode=='real_video' else tile['crack']
   if is_crack and tile['x']<=640<tile['x']+width:
    expected_physical.add(f"{cycles[frame]}:{tile['id'] if mode=='real_video' else tile['tile']}")
 duplicates=len(physical)-len(set(physical));unknown=sum(r['label'] is None for r in rows);max_error=max([r['center_error_px'] for r in rows if r['center_error_px'] is not None],default=None)
 result['real' if mode=='real_video' else 'synthetic']=dict(events=len(rows),unique_products=len(set(s['product_id'] for s in rows)),physical_products=len(set(physical)),duplicate_physical_products=duplicates,full_events=sum(s['full'] for s in rows),normal_events=sum(s['label']=='good' for s in rows),crack_events=sum(s['label']=='crack' for s in rows),unknown_events=unknown,center_mean_error_px=float(np.mean([r['center_error_px'] for r in rows if r['center_error_px'] is not None])) if rows else None,center_max_error_px=max_error,passed=bool(rows) and duplicates==0 and unknown==0 and max_error<=32 and all(r['full'] for r in rows),items=rows)
 result['real' if mode=='real_video' else 'synthetic']['max_observed_source_stall_ms']=max_source_stall
 result['real' if mode=='real_video' else 'synthetic']['passed'] &= max_source_stall<1000
 result['real' if mode=='real_video' else 'synthetic']['observed_cracked_products']=len(expected_physical)
 result['real' if mode=='real_video' else 'synthetic']['observed_cracked_products_without_evidence']=sorted(expected_physical-set(physical))
 result['real' if mode=='real_video' else 'synthetic']['passed'] &= expected_physical.issubset(set(physical))
 # Keep the original 32 px goal and strict failure visible. Product completeness,
 # identity and capture continuity are separate from this source precision goal.
 entry=result['real' if mode=='real_video' else 'synthetic']
 entry['centering_target_px']=32
 entry['centering_target_met']=max_error is not None and max_error<=32
 entry['functional_pass']=bool(rows) and duplicates==0 and unknown==0 and all(r['full'] for r in rows) and max_source_stall<1000 and expected_physical.issubset(set(physical)) and data['passed']
 entry['functional_pass'] &= entry['normal_events']==0
 entry['passed'] &= entry['normal_events']==0
(T/'motion_evidence_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:{a:b for a,b in v.items() if a!='items'} for k,v in result.items()}))
assert all(v['passed'] for v in result.values()),'Physical identity or centered-frame audit failed; evidence retained'
