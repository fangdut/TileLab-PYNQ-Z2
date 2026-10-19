from pathlib import Path
import json,tempfile,unittest
import numpy as np
from PIL import Image
from reference_tile import compare,integer_difference,calibrate,inspect,components,policy
from fixtures import frame,capture,add_defect

class ReferenceTileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.reference=frame('floral')
    def test_identical_print_is_not_a_defect(self):
        r,m,_=compare(self.reference,self.reference);self.assertEqual(r['status'],'COMPARED');self.assertFalse(r['alarm']);self.assertFalse(m.any());self.assertEqual(r['inspected_pixels'],250000);json.dumps(r)
    def test_fractional_resampling_keeps_edges_without_discarding_line(self):
        r,m,_=compare(self.reference,capture(self.reference,dx=.375,dy=-.25,noise=1))
        self.assertEqual(r['status'],'COMPARED',r);self.assertFalse(r['alarm'],r);self.assertAlmostEqual(r['registration']['dx'],.375,delta=.1)
        changed,truth=add_defect(self.reference,width=3,edge=True)
        r,m,_=compare(self.reference,capture(changed,dx=.375,dy=-.25,noise=.5))
        self.assertEqual(r['status'],'COMPARED',r);self.assertTrue(r['alarm']);self.assertGreater((m&truth).sum()/truth.sum(),.75)
    def test_small_translation_and_global_cast_keep_normal_print(self):
        current=capture(self.reference,dx=2,dy=-1,gains=(1.04,.97,1.02),offsets=(2,-3,1),noise=1)
        r,m,_=compare(self.reference,current);self.assertEqual(r['status'],'COMPARED',r);self.assertFalse(r['alarm'],r);self.assertAlmostEqual(r['registration']['dx'],2,delta=.2)
    def test_new_artificial_line_and_edge_pixels_are_inspected(self):
        current,truth=add_defect(self.reference,width=3,edge=True);r,m,_=compare(self.reference,current)
        self.assertEqual(r['status'],'COMPARED',r);self.assertTrue(r['alarm']);self.assertGreater((m&truth).sum()/truth.sum(),.75);self.assertTrue(m[:,0].any());self.assertTrue(m[:,-1].any())
    def test_invalid_images_never_become_normal_decisions(self):
        for current in [capture(self.reference,dx=6),capture(self.reference,gains=(.55,.55,.55)),frame('geometry'),capture(self.reference,angle=.8)]:
            r,m,_=compare(self.reference,current);self.assertEqual(r['status'],'REJECTED_INPUT',r);self.assertIsNone(r['alarm']);self.assertIsNone(m)
    def test_flat_surface_uses_fixture_boundary(self):
        a=frame('plain')
        for dx,dy in [(-2,1),(.375,-.25)]:
            r,m,_=compare(a,capture(a,dx=dx,dy=dy,noise=.5));self.assertEqual(r['status'],'COMPARED',r);self.assertFalse(r['alarm']);self.assertEqual(r['registration']['texture_mode'],'fixture_boundary')
    def test_integer_rounding_signed_offsets_clipping_and_strict_threshold(self):
        ref=np.array([[0,255,128],[10,10,10],[100,100,100]],np.uint8);current=np.array([[0,255,128],[10,10,10],[100,100,100]],np.uint8)
        n,s,h,l=integer_difference(ref,current,[256,256,256],[-20,20,0],np.zeros(3,np.uint8),20,19)
        self.assertEqual(n[0].tolist(),[0,255,128]);self.assertEqual(s.tolist(),[0,20,20]);self.assertEqual(h.tolist(),[False,False,False]);self.assertEqual(l.tolist(),[False,True,True])
    def test_bundle_integrity_pattern_identity_and_recalibration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'good.png';Image.fromarray(self.reference).save(source);bundle=root/'pattern_A';record=calibrate(source,'pattern-A',bundle)
            self.assertFalse(record['accuracy_qualified']);result,_,_=inspect(bundle,source,'pattern-A');self.assertFalse(result['alarm'])
            with self.assertRaises(ValueError):inspect(bundle,source,'pattern-B')
            with self.assertRaises(FileExistsError):calibrate(source,'pattern-A',bundle)
            with (bundle/'reference.png').open('ab') as f:f.write(b'tamper')
            with self.assertRaises(ValueError):inspect(bundle,source,'pattern-A')
    def test_no_implicit_image_resizing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'crop.png';Image.new('RGB',(500,500)).save(p)
            with self.assertRaises(ValueError):calibrate(p,'incomplete-context',Path(tmp)/'bundle')
    def test_run_components_preserve_diagonal_connectivity(self):
        weak=np.zeros((500,500),bool);strong=weak.copy()
        for i in range(40):weak[i,i]=True;strong[i,i]=True
        mask,regions=components(weak,strong,policy());self.assertEqual(len(regions),1);self.assertEqual(int(mask.sum()),40)

if __name__=='__main__':unittest.main()
