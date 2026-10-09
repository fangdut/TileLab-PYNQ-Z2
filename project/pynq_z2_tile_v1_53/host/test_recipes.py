import unittest,tempfile,json
from pathlib import Path
import recipes
from workstation import Station,Records,handler
class RecipeTests(unittest.TestCase):
    def test_center_metric_is_versioned_and_preserved(self):
        from test_events import packet
        from workstation import Bridge
        raw,d,m=packet();d[37]=4;d[38]=32;d[39]=0x80000011;m[1]=0x00010500
        f,img,mask=Bridge.decode_event(raw,d,m,1)
        self.assertEqual(f['selection_center_error_px'],8.5);self.assertTrue(f['selection_full_tile'])
        with tempfile.TemporaryDirectory() as t:
            records=Records(t);records.save(f,img,mask,'hardware_alarm')
            with self.assertRaises(ValueError):records.save(dict(f,selection_center_distance_x2=19),img,mask,'hardware_alarm')
            records.db.close()
        m[1]=0x00010400
        old,_,_=Bridge.decode_event(raw,d,m,1);self.assertNotIn('selection_center_error_px',old)
    def catalog(self):return [dict(id='old',name='old',threshold=36,sha256='oldhash'),dict(id='new',name='new',threshold=105,sha256='newhash',calibration_sha256='calhash')]
    def test_queued_old_frame_is_not_assigned_current_recipe(self):
        actual=recipes.evidence({'config_word':0x00f30007|(36<<8)},self.catalog())
        self.assertEqual(actual['recipe_id'],'old');self.assertEqual(actual['applied_threshold'],36)
    def test_new_frame_tracks_calibration_and_digest(self):
        actual=recipes.evidence({'config_word':0x80f30007|(105<<8)},self.catalog())
        self.assertEqual(actual['recipe_id'],'new');self.assertEqual(actual['recipe_calibration_sha256'],'calhash')
    def test_unknown_and_ambiguous_are_not_mislabeled(self):
        self.assertEqual(recipes.evidence({'config_word':72<<8},self.catalog())['recipe_id'],'custom_or_unknown')
        self.assertEqual(recipes.evidence({'config_word':36<<8},self.catalog()+[dict(id='duplicate',threshold=36)])['recipe_id'],'custom_or_unknown')
    def test_invalid_recipe_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'host';p.mkdir();(p/'recipes.json').write_text(json.dumps({'recipes':[{'id':'bad','threshold':True}]}))
            with self.assertRaises(ValueError):recipes.load(t)
    def test_api_unknown_recipe_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as t:
            st=Station(root=t,bridge=object())
            try:
                before=(st.threshold,st.recipe_id)
                with self.assertRaises(ValueError):st.action(dict(op='recipe',value='../bad'))
                self.assertEqual((st.threshold,st.recipe_id),before)
            finally:st.exit=True;st.worker.join(2);st.records.db.close()
    def test_same_threshold_requires_matching_hardware_algorithm(self):
        catalog=[dict(id='weak',name='weak',threshold=89,sha256='digest',requires_weak_support=True)]
        old=recipes.evidence({'config_word':0x00f30007|(89<<8)},catalog)
        new=recipes.evidence({'config_word':0x01f30007|(89<<8)},catalog)
        self.assertEqual(old['recipe_id'],'custom_or_unknown');self.assertIsNone(old['applied_low_threshold'])
        self.assertEqual(new['recipe_id'],'weak');self.assertEqual(new['applied_low_threshold'],45)
    def test_algorithm_low_threshold_uses_captured_configuration(self):
        actual=recipes.evidence({'config_word':0x01f30007|(255<<8)},[])
        self.assertEqual(actual['applied_low_threshold'],128);self.assertTrue(actual['weak_support_enabled'])
if __name__=='__main__':unittest.main()
