import unittest
from frame_rate import FrameRate

class RateTests(unittest.TestCase):
    def test_delayed_packets_do_not_report_short_interval_spikes(self):
        r=FrameRate();self.assertIsNone(r.observe(100,0,1))
        self.assertIsNone(r.observe(112,.19,1))
        self.assertEqual(r.observe(232,2.2,1),60.0)
        self.assertEqual(r.observe(233,2.21,1),60.0)
    def test_reboot_clears_previous_rate(self):
        r=FrameRate();r.observe(100,0,1);r.observe(220,2,1)
        self.assertIsNone(r.observe(1,2.1,2))
    def test_pause_gap_and_explicit_reset(self):
        r=FrameRate();r.observe(100,0,1);r.observe(220,2,1)
        self.assertIsNone(r.observe(820,12,1));r.reset()
        self.assertIsNone(r.observe(900,13,1))
    def test_counter_wrap(self):
        r=FrameRate();r.observe(0xffffffc0,0,1)
        self.assertEqual(r.observe(56,2,1),60.0)
    def test_counter_reset_same_boot(self):
        r=FrameRate();r.observe(1000,0,1)
        self.assertIsNone(r.observe(10,2,1))

if __name__=='__main__':unittest.main()
