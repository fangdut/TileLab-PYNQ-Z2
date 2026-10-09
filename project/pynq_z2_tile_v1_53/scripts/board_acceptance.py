"""Actual-board acceptance through the local workstation API.

The Python detector is an independent verification oracle, never the runtime
source of boxes or event decisions. It compares the actual captured pixels.
"""
from pathlib import Path
import json,time,urllib.request,sys,io
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'models'))
from valley_reference import detect
BASE='http://127.0.0.1:8770'
OUT=ROOT/'reports/board_acceptance';OUT.mkdir(exist_ok=True)
def get(path):return urllib.request.urlopen(BASE+path,timeout=10).read()
def state():return json.loads(get('/api/state'))
def action(op,**kw):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/action',data=json.dumps(dict(op=op,**kw)).encode(),headers={'Content-Type':'application/json'}),timeout=10))
def shot():
    before=state()['captures'];action('capture');deadline=time.monotonic()+110
    while time.monotonic()<deadline:
        s=state()
        if s['error']:raise RuntimeError(s['error'])
        if s['captures']>before and not s['busy']:return s
        time.sleep(.25)
    raise RuntimeError('Timed out waiting for actual board frame')
rows=[]
action('pause');action('threshold',value=36)
for idx in range(4):
    action('display',value=f'station_{idx}');time.sleep(1)
    s=shot();f=s['frame'];raw=get('/api/image');mask=get('/api/image?mask=1')
    (OUT/f'station_{idx}_original.png').write_bytes(raw);(OUT/f'station_{idx}_pl_mask.png').write_bytes(mask)
    original=Image.open(io.BytesIO(raw));actual=np.asarray(Image.open(io.BytesIO(mask)))>0
    expected,ref=detect(original,threshold=36)
    different=int(np.count_nonzero(actual!=expected))
    row=dict(station=idx,kind=('normal','fine_crack','reflection','wider_crack')[idx],
        expected_alarm=idx in (1,3),hardware=f,reference_on_actual_pixels=ref,mask_mismatch_pixels=different,
        passed=bool(different==0 and f['alarm']==(idx in (1,3)) and f['boxes']==ref['boxes']))
    rows.append(row);print(json.dumps(row),flush=True)
    (OUT/'static_results.json').write_text(json.dumps(rows,indent=2))
    if not row['passed']:raise AssertionError('Actual-board acceptance failed; inspect saved original/mask')
print('BOARD STATIC PASS: four full-resolution captures and PL masks match independent reference',flush=True)
