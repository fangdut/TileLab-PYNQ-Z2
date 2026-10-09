"""Physical FPGA mode changes at product gaps, exact captured masks/regions.
This is a regression on known HDMI photos, not a blind accuracy estimate.
"""
from pathlib import Path
import sys,json,time,io
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'host'),str(R/'models')]
from workstation import EthernetBridge
from weak_reference import detect
from valley_reference import detect as baseline
from regions_reference import regions
from board_v18_continuous import action,state,wait_idle,read_player
O=R/'reports/v132/mode_boundary';O.mkdir(parents=True,exist_ok=True)

def run():
 wait_idle();b=EthernetBridge('169.254.200.10');rows=[];threshold=90
 def display(source):
  action('display',value=source);end=time.monotonic()+6
  while read_player().get('source')!=source:
   if time.monotonic()>end:raise TimeoutError(source)
   time.sleep(.05)
  time.sleep(.3)
 def shot(ack=True):
  f,im,m=b.capture(threshold)
  if ack:b.ack(f)
  return f,im,m
 def ready(en,passes,t):
  nonlocal threshold
  threshold=t;b.enhance=en;b.passes=passes;display('station_6')
  for _ in range(16):
   f,_,_=shot();cfg=f['config_word']
   if ((cfg>>8)&255)==t and bool(cfg&(1<<24))==en and bool(cfg&(1<<25))==(passes==4) and not b.stats()['depth']:return
  raise AssertionError('Mode did not commit at product gap')
 def check(name,en,passes,t):
  f,im,m=shot();cfg=f['config_word'];photo=Image.open(io.BytesIO(im))
  expected,_=detect(photo,threshold=t,passes=passes) if en else baseline(photo,threshold=t)
  actual=np.asarray(Image.open(io.BytesIO(m)))>0;rr=regions(expected)
  assert ((cfg>>8)&255)==t and bool(cfg&(1<<24))==en and bool(cfg&(1<<25))==(passes==4)
  assert np.array_equal(actual,expected) and f['boxes']==rr['boxes'] and f['region_areas']==rr['areas']
  key=f'{len(rows):02d}_{name}';(O/(key+'.png')).write_bytes(im);(O/(key+'_mask.png')).write_bytes(m)
  rows.append(dict(phase=name,frame=f,exact=True,passes=passes if en else 0,threshold=t));return f
 try:
  ready(True,4,90);before=b.stats();assert before['version']==0x11800
  display('real_005');shot();f=check('quad',True,4,90);assert f['alarm'] and b.stats()['current_product_id']>0
  # Preserve one queued event while requesting a new mode. Read must remain
  # attributed to its captured recipe, regardless of host request-time values.
  old=b.capture(threshold);b.passes=2;threshold=89;b.configure(threshold)
  same=b.capture(threshold)
  assert all(same[0][k]==old[0][k] for k in ('boot_id','event_id','frame_id','config_word','pixel_crc32'))
  assert same[1:]==old[1:];b.ack(same[0])
  for _ in range(3):check('two_requested_but_same_tile_holds_quad',True,4,90)
  ready(True,2,89);display('real_005');shot();assert check('legacy_two_after_gap',True,2,89)['alarm']
  ready(False,2,89);display('real_005');shot();assert not check('high_only_after_gap',False,2,89)['alarm']
  # The normal training counterexample is deliberately retained and checked.
  ready(True,4,89);display('calib_162');shot();bad=check('rejected_high89_normal',True,4,89)
  ready(True,4,90);display('calib_162');shot();fixed=check('frozen_high90_normal',True,4,90)
  assert bad['alarm'] and not fixed['alarm']
  after=b.stats();assert all(after[k]==before[k] for k in ('gaps','invalid','dropped','ack_errors','descriptor_crc_errors'))
  result=dict(passed=True,queued_recipe_preserved=True,before=before,after=after,items=rows,scope=__doc__)
  (O/'summary.json').write_text(json.dumps(result,indent=2));print('PASS actual product-gap modes, queued recipe identity and normal counterexample',flush=True)
 finally:display('station_6');b.close()
if __name__=='__main__':run()
