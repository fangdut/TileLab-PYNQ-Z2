import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'models'))
from support_profiles_v155 import compute_features,mask_from_features
from directional_mean_reference import directional_mean_score
from weak_reference import grow

class SupportProfileTests(unittest.TestCase):
 def test_directional_extension_is_aligned_and_bounded(self):
  planes=[np.zeros((48,64),np.uint8) for _ in range(5)];dirs=np.zeros((4,48,64),bool);keep=np.ones((48,64),bool)
  planes[0][20,5]=100;planes[2][20,5:40]=21;dirs[0,20,5:40]=True
  features=(*planes,dirs)
  sensitive=mask_from_features(features,keep,'sensitive');yy,xx=np.where(sensitive)
  self.assertEqual(yy.tolist(),[20]*9);self.assertEqual(xx.tolist(),list(range(5,14)))
  self.assertEqual(int(mask_from_features(features,keep,'v154').sum()),1)
  dirs[0]=False;dirs[1,20,5:40]=True
  self.assertEqual(int(mask_from_features(features,keep,'sensitive').sum()),1)
 def test_roi_prevents_growth_across_excluded_gap(self):
  planes=[np.zeros((48,64),np.uint8) for _ in range(5)];dirs=np.zeros((4,48,64),bool);keep=np.ones((48,64),bool)
  planes[0][20,5]=100;dirs[0,20,5:40]=True;keep[:,9]=False
  mask=mask_from_features((*planes,dirs),keep,'sensitive')
  self.assertEqual(np.where(mask)[1].tolist(),[5,6,7,8])
 def test_old_fixed_profile_matches_prior_integer_features(self):
  rng=np.random.default_rng(155);a=rng.integers(0,256,(72,96),dtype=np.uint8);f=compute_features(a)
  self.assertTrue(np.array_equal(f[2],directional_mean_score(a,8)))
  self.assertTrue(np.array_equal(f[3],directional_mean_score(a,16)))
  keep=np.zeros(a.shape,bool);keep[20:52,20:76]=True
  n,w,s,l,_,_=f;seed=((n>90)|(s>40)|(l>48))&keep;weak=((n>45)|(w>45)|(s>20)|(l>24))&keep
  for _ in range(4):seed=grow(seed,weak,3);seed[[0,-1],:]=False;seed[:,[0,-1]]=False
  self.assertTrue(np.array_equal(seed&keep,mask_from_features(f,keep,'v154')))
 def test_profile_specific_strong_threshold_is_strict(self):
  planes=[np.zeros((48,64),np.uint8) for _ in range(5)];dirs=np.zeros((4,48,64),bool);keep=np.ones((48,64),bool)
  planes[4][20,20]=60;planes[4][20,40]=61;f=(*planes,dirs)
  self.assertEqual(np.where(mask_from_features(f,keep,'conservative'))[1].tolist(),[40])
  self.assertFalse(mask_from_features(f,keep,'sensitive').any())
if __name__=='__main__':unittest.main()
