"""Synthetic attribution/invariant checks independent of historical images."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'models'))
import numpy as np
from miss_diagnostics import diagnose, box_coverage

class DiagnosticsTests(unittest.TestCase):
    def test_partition_has_distinct_causes(self):
        s=np.zeros((30,40),int); t=np.zeros_like(s,bool); roi=np.ones_like(t)
        s[10,10]=100
        # Each case has only one eligible cause in the declared decision order.
        for y,x,v in [(0,0,100),(1,1,20),(20,30,60),(10,12,60),(10,11,60)]:
            t[y,x]=True;s[y,x]=v
        roi[0,0]=False
        # Disconnect (10,12) from seed without disconnecting the support case.
        s[10,12]=0;t[10,12]=False;s[12,10]=60;t[12,10]=True
        _,d=diagnose(s,t,roi)
        self.assertEqual(d['categories'],dict(outside_roi=1,response_at_or_below_low=1,
            no_seed_within_growth_radius=1,no_weak_path_within_growth_steps=1,
            three_neighbor_support_requirement=1))

    def test_empty_and_all_strong(self):
        for v in (0,100):
            s=np.full((5,5),v); t=np.ones_like(s,bool)
            mask,d=diagnose(s,t,t)
            self.assertEqual(d['fn'],25 if v==0 else 0)
            self.assertEqual(d['tp'],0 if v==0 else 25)
            self.assertEqual(sum(d['categories'].values()),d['fn'])

    def test_radius_and_path(self):
        s=np.zeros((80,80),int);s[40,40]=100;s[40,41:76]=60
        t=np.zeros_like(s,bool);t[40,40:76]=True
        _,d=diagnose(s,t,np.ones_like(t))
        for row in d['optimistic_reachability']:
            self.assertEqual(row['weak_connected_truth'],row['steps']+1)
            self.assertEqual(row['unconstrained_truth'],row['steps']+1)

    def test_random_partition_bounds(self):
        rng=np.random.default_rng(151)
        for _ in range(12):
            s=rng.integers(0,130,(20,25));t=rng.random(s.shape)>.5;r=rng.random(s.shape)>.1
            m,d=diagnose(s,t,r)
            self.assertEqual(sum(d['categories'].values()),d['fn'])
            self.assertEqual(sum(b['truth'] for b in d['score_bands'].values()),d['truth'])
            self.assertEqual(sum(b['missed'] for b in d['score_bands'].values()),d['fn'])
            self.assertFalse((m&~r).any())
            c=d['optimistic_reachability']
            for a,b in zip(c,c[1:]):
                self.assertLessEqual(a['weak_connected_truth'],b['weak_connected_truth'])
                self.assertLessEqual(a['unconstrained_truth'],b['unconstrained_truth'])

    def test_box_union_no_double_count(self):
        t=np.ones((4,4),bool)
        self.assertEqual(box_coverage(t,[[0,0,2,2],[1,1,3,3]]),
                         dict(covered_truth=14,truth=16,box_pixels=14))
        self.assertEqual(box_coverage(t,[])['covered_truth'],0)
        with self.assertRaises(ValueError):box_coverage(t,[[0,0,4,3]])

    def test_validation(self):
        a=np.ones((5,5),bool)
        for args in [(a,a[:2],a),(a,a.astype(int),a)]:
            with self.assertRaises(ValueError):diagnose(*args)
        with self.assertRaises(ValueError):diagnose(a,a,a,high=30,low=45)

if __name__=='__main__':unittest.main()
