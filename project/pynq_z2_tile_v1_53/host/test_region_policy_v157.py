import sys,json,hashlib,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'models'))
from region_quality_reference_v157 import quality_regions
from regions_reference import regions

class RegionalEvidencePolicyTests(unittest.TestCase):
 def pattern(self,count,credible):
  mask=np.zeros((128,256),bool);trust=np.zeros_like(mask)
  for k in range(count):mask[32+k//32,32+k%32]=1
  for k in range(credible):trust[32+k//32,32+k%32]=1
  return mask,trust
 def test_minimum_credible_support(self):
  for credible,accepted in [(15,False),(16,True)]:
   m,t=self.pattern(64,credible);self.assertEqual(bool(quality_regions(m,t)['boxes']),accepted)
 def test_fraction_boundary(self):
  for count,accepted in [(64,True),(65,False)]:
   m,t=self.pattern(count,16);self.assertEqual(bool(quality_regions(m,t)['boxes']),accepted)
 def test_evidence_outside_candidates_does_not_count(self):
  m,t=self.pattern(64,0);t[90:120,32:160]=1;self.assertFalse(quality_regions(m,t)['boxes'])
 def test_disabled_is_exact_legacy(self):
  rng=np.random.default_rng(157)
  for _ in range(16):
   m=rng.random((128,256))<.003;t=rng.random(m.shape)<.5
   got=quality_regions(m,t,False);expected=regions(m)
   for key in ['boxes','areas','overflow']:self.assertEqual(got[key],expected[key])
 def test_filtering_precedes_eight_region_limit(self):
  m=np.zeros((256,1024),bool);t=np.zeros_like(m)
  for j in range(10):
   x=32+(j%5)*192;y=32+(j//5)*128;m[y:y+32,x:x+2]=1
   if j==9:t[y:y+32,x:x+2]=1
  self.assertTrue(quality_regions(m,t,False)['overflow']);got=quality_regions(m,t)
  self.assertEqual(len(got['boxes']),1);self.assertFalse(got['overflow']);self.assertEqual(got['trusted'],[64])
 def test_frozen_profile_matches_sources_and_runtime(self):
  p=json.loads((ROOT/'models/v159_frozen_profile.json').read_text());self.assertEqual(p['model_id'],0xd06b3b9b)
  self.assertEqual((p['min_trusted'],p['evidence_shift']),(16,2))
  for rel,digest in p['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),digest)
 def test_raw_candidates_do_not_bypass_regional_alarm(self):
  import test_events
  from workstation import Bridge
  raw,d,m=test_events.packet();m[1]=0x13100
  d[7]=(90<<8)|(3<<16)|(1<<23)|(1<<24)|(1<<25)|(1<<27)|(1<<28)|(3<<29)
  d[9]=0
  frame,_,mask=Bridge.decode_event(raw,d,m,1)
  import io
  from PIL import Image
  self.assertEqual(frame['candidate_pixels'],200);self.assertEqual(int(np.count_nonzero(np.asarray(Image.open(io.BytesIO(mask))))),200)
  self.assertFalse(frame['alarm']);self.assertEqual(frame['boxes'],[]);self.assertTrue(frame['region_evidence_enabled'])
  self.assertEqual(frame['region_min_trusted'],16)
  d[9]=1;frame,_,_=Bridge.decode_event(raw,d,m,1);self.assertTrue(frame['alarm'])

if __name__=='__main__':unittest.main()
