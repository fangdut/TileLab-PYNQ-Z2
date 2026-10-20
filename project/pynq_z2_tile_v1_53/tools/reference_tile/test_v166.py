from pathlib import Path
import copy,json,tempfile,unittest
import numpy as np
from PIL import Image
from fixtures import frame,capture,add_defect
import reference_v166 as v
from qualification_v166 import metrics,validate,wilson,evaluate

class V166Tests(unittest.TestCase):
    def test_reciprocal_mean_is_exact_over_all_nine_pixel_sums(self):
        sums=np.arange(9*255+1,dtype=np.int64)
        np.testing.assert_array_equal((sums+4)//9,((sums+4)*7282)>>16)
    def test_jpeg_pattern_edges_keep_normal_and_one_pixel_luma_line(self):
        ref=frame('floral');r,m,_=v.compare(ref,capture(ref,jpeg=92));self.assertFalse(r['alarm'],r);self.assertIsNotNone(m)
        cur,truth=add_defect(ref,1);r,m,_=v.compare(ref,capture(cur,jpeg=92));self.assertTrue(r['alarm'],r);self.assertGreater((m&truth).sum()/truth.sum(),.95)
    def test_isoluminant_thin_change_is_not_erased(self):
        ref=frame('plain');_,truth=add_defect(ref,1);cur=ref.copy();tile=cur[110:610,390:890].astype(np.int16);tile[truth]+=np.array([40,0,-40]);cur[110:610,390:890]=tile.astype(np.uint8)
        r,m,_=v.compare(ref,cur);self.assertTrue(r['alarm'],r);self.assertEqual(int((m&truth).sum()),int(truth.sum()))
    def test_full_roi_edge_line_coverage(self):
        ref=frame('geometry');cur,truth=add_defect(ref,3,False,True);r,m,_=v.compare(ref,cur)
        self.assertTrue(r['alarm']);self.assertEqual(r['inspected_pixels'],250000);self.assertTrue(m[:,0].any());self.assertTrue(m[:,-1].any());self.assertGreater((m&truth).sum()/truth.sum(),.8)
    def test_new_bundles_are_integrity_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'good.png';Image.fromarray(frame('plain')).save(p);bundle=root/'bundle';v.calibrate(p,'plain-A',bundle)
            self.assertFalse(v.inspect(bundle,p,'plain-A')[0]['alarm'])
            with self.assertRaises(ValueError):v.inspect(bundle,p,'other')
            with self.assertRaises(FileExistsError):v.calibrate(p,'plain-A',bundle)
            record=json.loads((bundle/'calibration.json').read_text());record['policy']['high']=255;(bundle/'calibration.json').write_text(json.dumps(record))
            with self.assertRaises(ValueError):v.inspect(bundle,p,'plain-A')
    def test_rejects_are_in_denominator_and_fail_the_gate(self):
        normals=[dict(label='good',alarm=False,tp=0,pixel_coverage=None) for _ in range(400)]
        positives=[dict(label='crack',alarm=True,tp=100,pixel_coverage=.9) for _ in range(100)]
        self.assertTrue(metrics(normals+positives)['passed'])
        normals[0]['alarm']=None;m=metrics(normals+positives);self.assertFalse(m['passed']);self.assertEqual(m['negative'],400);self.assertEqual(m['negative_rejects'],1)
        self.assertGreater(wilson(0,33)[1],.10);self.assertLess(wilson(0,400)[1],.01)
    def test_synthetic_empty_and_self_comparison_evidence_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);image=root/'good.png';Image.fromarray(frame()).save(image)
            manifest=dict(schema=1,scope='REAL_INDEPENDENT_SAME_PATTERN_BLIND_TEST',frozen_implementation=v.implementation(),frozen_policy_sha256=v.hashlib.sha256(v.base.canonical(v.policy())).hexdigest(),source_and_labels_reviewed=True,materials=['A'],references=[dict(material_id='A',physical_tile_id='tile-1',image='good.png',sha256=v.base.sha(image),label='good',real_photo=True)],samples=[])
            self.assertFalse(evaluate(manifest,root)['qualified'])
            manifest['samples']=[dict(material_id='A',physical_tile_id='tile-1',image='good.png',sha256=v.base.sha(image),label='good',real_photo=True,augmented=False,opened_for_tuning=False)]
            errors,_=validate(manifest,root);self.assertTrue(any('Calibration tile reused' in e for e in errors));self.assertTrue(any('Duplicate decoded' in e for e in errors))
            manifest['samples'][0]['augmented']=True;self.assertTrue(any('Synthetic' in e for e in validate(manifest,root)[0]))

if __name__=='__main__':unittest.main()
