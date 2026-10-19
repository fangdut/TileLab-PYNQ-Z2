from pathlib import Path
import json,unittest
import numpy as np
from detector import ROOT,features
from fine_integer_reference import predict

class ReferenceTests(unittest.TestCase):
    def test_frozen_rtl_feature_and_integer_score_vectors(self):
        # Reuse the actual small RGB core stimulus and exact pre-RTL oracle.
        p=ROOT/'reports/v159/core_vectors02'
        native=np.array([int(s,16) for s in (p/'input.mem').read_text().split()],np.uint32).reshape(80,96)
        # Native HDMI word order is R/B/G; the offline API accepts ordinary RGB.
        rgb=np.stack([(native>>16)&255,native&255,(native>>8)&255],axis=-1).astype(np.uint8)
        frame=np.zeros((720,1280,3),np.uint8);frame[0:80,0:96]=rgb
        # The small stimulus has different outer borders. Compare only pixels
        # whose complete radius16 neighborhood is inside that stimulus.
        actual=features(frame)[0][:80,:96]
        packed=[int(s,16) for s in (p/'features.mem').read_text().split()]
        expected=np.array([[(v>>(8*i))&255 for i in range(14)] for v in packed],np.uint8).reshape(80,96,14)
        self.assertTrue(np.array_equal(actual[16:64,16:80],expected[16:64,16:80]))
        model=json.loads((ROOT/'models/v159_integer_model.json').read_text())
        scores=np.array([int(s,16) for s in (p/'model_score.mem').read_text().split()],np.uint32).view(np.int32).reshape(80,96)
        self.assertTrue(np.array_equal(predict(expected[16:64,16:80],model),scores[16:64,16:80]))

if __name__=='__main__':unittest.main()
