"""Verify moving HDMI samples against the offline oracle on actual board pixels."""
from pathlib import Path
import json,time,urllib.request,sys,io,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'models'))
from valley_reference import detect
OUT=ROOT/'reports/board_acceptance';OUT.mkdir(exist_ok=True)
BASE='http://127.0.0.1:8770'
def get(path):return urllib.request.urlopen(BASE+path,timeout=10).read()
def state():return json.loads(get('/api/state'))
def action(op,**kw):
 return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/action',data=json.dumps(dict(op=op,**kw)).encode(),headers={'Content-Type':'application/json'}),timeout=10))
action('pause');action('threshold',value=36);action('display',value='video');time.sleep(2)
before=state()['captures'];action('start');rows=[];seen=before;deadline=time.monotonic()+420;next_sample=0
try:
 while len(rows)<12 and time.monotonic()<deadline:
  s=state()
  if s['error']:raise RuntimeError(s['error'])
  if s['captures']==seen or time.monotonic()<next_sample:time.sleep(.25);continue
  seen=s['captures'];f=s['frame'];key=urllib.parse.quote(str(f['frame_id'])+'_'+f['acquired_at'])
  raw=get('/api/image?frame='+key);mask=get('/api/image?mask=1&frame='+key)
  original=Image.open(io.BytesIO(raw));actual=np.asarray(Image.open(io.BytesIO(mask)))>0
  expected,ref=detect(original,threshold=36);diff=int(np.count_nonzero(actual!=expected))
  i=len(rows);(OUT/f'motion_{i:02}_original.png').write_bytes(raw);(OUT/f'motion_{i:02}_pl_mask.png').write_bytes(mask)
  row=dict(index=i,hardware=f,reference_on_actual_pixels=ref,mask_mismatch_pixels=diff,
   sha256=hashlib.sha256(raw).hexdigest(),passed=bool(diff==0 and f['boxes']==ref['boxes'] and f['alarm']==ref['alarm']))
  rows.append(row);next_sample=time.monotonic()+3.1
  (OUT/'motion_results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
  if not row['passed']:raise AssertionError('Moving hardware sample disagrees with reference')
finally:action('pause')
s=state();(OUT/'motion_archive_state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
assert len(rows)==12 and len({r['sha256'] for r in rows})>3,'Insufficient moving samples'
assert any(r['hardware']['alarm'] for r in rows) and any(not r['hardware']['alarm'] for r in rows),'Need both positive and normal samples'
assert any(r['reason']=='hardware_alarm' for r in s['records']),'No real automatic event saved'
print('BOARD MOTION PASS: 12 sampled frames, exact masks and actual automatic archive; not an all-frame guarantee',flush=True)
