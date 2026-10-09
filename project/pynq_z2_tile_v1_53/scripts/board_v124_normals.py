"""Reacquire 230 known normal calibration photos; freeze T90/four passes.
No fitting or selection is performed. Store every result/hash but only a few
representative images unless a mismatch/false alarm requires evidence.
"""
from pathlib import Path
import sys,time,json,io,hashlib
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'host'),str(R/'models')]
from workstation import EthernetBridge
from weak_reference import detect
from regions_reference import regions
from board_v18_continuous import action,wait_idle,read_player,barcode
O=R/'reports/v132/normal_board';O.mkdir(parents=True,exist_ok=True)

def run():
 wait_idle();b=EthernetBridge('169.254.200.10');b.passes=4;rows=[]
 def source(name):
  action('display',value=name);end=time.monotonic()+5
  while read_player().get('source')!=name:
   if time.monotonic()>end:raise TimeoutError(name)
   time.sleep(.035)
  time.sleep(.12)
 def shot():
  f,im,m=b.capture(90);b.ack(f);return f,im,m
 try:
  source('station_6')
  for _ in range(16):
   f,_,_=shot()
   if f['config_word']&(1<<25) and ((f['config_word']>>8)&255)==90 and not b.stats()['depth']:break
  else:raise AssertionError('Recipe did not apply')
  before=b.stats();assert before['version']==0x11800
  for n in range(230):
   source(f'calib_{n:03d}')
   for _ in range(8):
    f,im,m=shot()
    if barcode(im)==n+1:break
   else:raise AssertionError('Captured HDMI barcode mismatch')
   actual=np.asarray(Image.open(io.BytesIO(m)))>0;expected,_=detect(Image.open(io.BytesIO(im)),threshold=90,passes=4);rr=regions(expected)
   exact=np.array_equal(actual,expected) and f['boxes']==rr['boxes'] and f['region_areas']==rr['areas']
   valid=f['config_word']&(1<<25) and ((f['config_word']>>8)&255)==90
   assert all(f[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
   row=dict(index=n,frame=f,exact=bool(exact),recipe_matches=bool(valid),image_sha256=hashlib.sha256(im).hexdigest(),mask_sha256=hashlib.sha256(m).hexdigest());rows.append(row)
   if n in (0,162,229) or not exact or not valid or f['alarm']:
    (O/f'calib_{n:03d}.png').write_bytes(im);(O/f'calib_{n:03d}_mask.png').write_bytes(m)
   (O/'progress.json').write_text(json.dumps(rows,indent=2));assert exact and valid,(n,row)
   if (n+1)%20==0:print('Actual normal photos',n+1,'alarms',sum(r['frame']['alarm'] for r in rows),flush=True)
  source('station_6')
  while b.stats()['depth']:shot()
  after=b.stats();alarms=sum(r['frame']['alarm'] for r in rows)
  result=dict(passed=len(rows)==230 and alarms==0 and all(after[k]==before[k] for k in ('invalid','gaps','dropped','ack_errors','descriptor_crc_errors')),scope=__doc__,high=90,passes=4,images=len(rows),alarms=alarms,before=before,after=after,items=rows)
  (O/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('items','before','after')}),flush=True);assert result['passed']
 finally:source('station_6');b.close()
if __name__=='__main__':run()
