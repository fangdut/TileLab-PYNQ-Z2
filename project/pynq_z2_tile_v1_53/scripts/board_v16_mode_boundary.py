"""Actual FPGA enhanced/baseline switch at a product gap, with exact masks."""
from pathlib import Path
import sys,json,time,io
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'host'),str(R/'models')]
from workstation import EthernetBridge
from weak_reference import detect
from valley_reference import detect as baseline
from regions_reference import regions
import board_v13_acceptance as t
OUT=R/'reports/v132';OUT.mkdir(exist_ok=True)
def run():
 t.action('pause')
 while t.state()['busy']:time.sleep(.05)
 t.action('disconnect');bridge=EthernetBridge('169.254.200.10');evidence=[]
 def shot():
  f,im,m=bridge.capture(89);bridge.ack(f);return f,im,m
 def ready(enhance):
  bridge.enhance=enhance;t.action('display',value='station_6');time.sleep(.35)
  for _ in range(12):
   f,im,m=shot()
   if bool(f['config_word']&(1<<24))==enhance and (f['config_word']>>8)&255==89 and bridge.stats()['depth']==0:return
  raise AssertionError('Requested mode did not apply at product gap')
 def check(name,en):
  f,im,m=shot();expected,_=(detect if en else baseline)(Image.open(io.BytesIO(im)),threshold=89)
  actual=np.asarray(Image.open(io.BytesIO(m)))>0;rr=regions(expected)
  assert bool(f['config_word']&(1<<24))==en and np.array_equal(actual,expected) and f['boxes']==rr['boxes']
  evidence.append(dict(phase=name,frame=f,exact=True));return f
 try:
  ready(True);t.action('display',value='real_005');time.sleep(.35);shot();f=check('enhanced',True);assert f['alarm']
  assert bridge.stats()['current_product_id']>0
  bridge.enhance=False
  for _ in range(4):check('request_baseline_while_same_tile_still_active',True)
  ready(False);t.action('display',value='real_005');time.sleep(.35);shot();f=check('baseline_after_product_gap',False);assert not f['alarm']
  ready(True);t.action('display',value='real_005');time.sleep(.35);shot();check('enhanced_restored',True)
  (OUT/'mode_boundary.json').write_text(json.dumps(dict(passed=True,items=evidence),indent=2));print('MODE BOUNDARY PASS; same-tile parameters held, baseline exact, enhancement restored',flush=True)
 finally:t.action('display',value='station_6');bridge.close()
if __name__=='__main__':run()
