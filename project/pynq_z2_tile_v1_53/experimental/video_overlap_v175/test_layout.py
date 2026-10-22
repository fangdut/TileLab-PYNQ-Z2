"""Reject snapshots of the wrong DDR ownership layout before reading images."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/texture_v170'))
from video_layout import validate_frame_base,FRAME_BASES,OVERLAP_VERSION
class Layout(unittest.TestCase):
    def test_all_four_owned_slots(self):
        for base in FRAME_BASES:self.assertEqual(validate_frame_base(OVERLAP_VERSION,base),base)
    def test_model_result_and_unaligned_slots_are_rejected(self):
        for base in (0,0x04000000,0x07000000,0x08000000,0x10000000,0x06000004,0x06800100,0x06bffffc):
            with self.assertRaises(ValueError):validate_frame_base(OVERLAP_VERSION,base)
    def test_legacy_fixed_slot_is_preserved(self):
        for version in (0x17100001,0x17200001):
            self.assertEqual(validate_frame_base(version,FRAME_BASES[0]),FRAME_BASES[0])
            for base in FRAME_BASES[1:]:
                with self.assertRaises(ValueError):validate_frame_base(version,base)
    def test_unknown_layout_is_not_guessed(self):
        with self.assertRaises(ValueError):validate_frame_base(0x17600001,FRAME_BASES[0])
if __name__=='__main__':unittest.main()
