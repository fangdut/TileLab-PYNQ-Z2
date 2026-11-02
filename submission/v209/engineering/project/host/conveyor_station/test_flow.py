# SPDX-License-Identifier: MIT
"""Boundary tests for pixel binding and result lifetime; no board access."""
import io, tempfile, unittest, time
from pathlib import Path
from PIL import Image
from server import Conveyor, sha


class API:
    def __init__(self):
        self.s=dict(session='one',phase='READY',cycle=None,
                    closed_loop=dict(calibrated=True),connection={},automatic_pass_policy={'enabled':True})
    def state(self): return self.s.copy()


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.image=Image.new('RGB',(8,8),(12,13,14))
        out=io.BytesIO();self.image.save(out,format='PNG');self.raw=out.getvalue()
        file=self.root/'source.png';file.write_bytes(self.raw)
        row=dict(id='photo',file=str(file),name='test',sha256=sha(self.raw))
        self.api=API();self.flow=Conveyor(self.api,{'photo':row},self.root/'store')
        self.flow.action(dict(run=self.flow.run,op='start',queue=['photo'],incoming=3))

    def tearDown(self): self.temp.cleanup()

    def test_capture_rejects_wrong_pixels_and_stale_token(self):
        self.flow.transition('CAPTURE')
        out=io.BytesIO();Image.new('RGB',(8,8),'red').save(out,format='PNG')
        with self.assertRaisesRegex(ValueError,'像素不一致'):
            self.flow.capture(self.flow.token,out.getvalue())
        with self.assertRaisesRegex(ValueError,'过期'):
            self.flow.capture('old',self.raw)
        self.assertEqual(self.flow.phase,'CAPTURE')
        self.assertIsNone(self.flow.capture_meta)

    def test_cannot_review_before_fpga(self):
        with self.assertRaisesRegex(ValueError,'没有待复核'):
            self.flow.action(dict(run=self.flow.run,op='review'))
        self.assertEqual(self.flow.phase,'MOVING')

    def test_missing_renderer_stops_instead_of_skipping(self):
        self.flow.transition('CAPTURE');self.flow.since-=21;self.flow.tick()
        self.assertEqual(self.flow.phase,'FAULT')
        self.assertFalse(self.flow.enabled)

    def test_station_restart_invalidates_held_result(self):
        self.api.s['session']='two';self.flow.tick()
        self.assertEqual(self.flow.phase,'FAULT')

    def test_new_tile_has_no_old_cycle_or_capture(self):
        self.flow.cycle_id='old';self.flow.capture_meta={'old':1}
        self.flow._begin()
        self.assertIsNone(self.flow.cycle_id)
        self.assertIsNone(self.flow.snapshot()['cycle'])
        self.assertIsNone(self.flow.capture_meta)

    def test_acknowledgement_survives_next_tile(self):
        self.flow.action(dict(run=self.flow.run,op='ack_review',confirmed=True))
        self.flow._begin()
        self.assertTrue(self.flow.snapshot()['review_ack'])

    def test_unknown_result_cannot_move_past_review(self):
        self.flow.motion_t0-=30
        self.flow.phase='INSPECTING'
        self.assertEqual(self.flow.position(),780)
        self.assertTrue(self.flow.snapshot()['motion']['waiting_for_result'])

    def test_early_pass_keeps_original_constant_motion(self):
        original=self.flow.motion_t0
        x=self.flow.position();self.flow.permit_pass()
        self.assertIsNone(self.flow.release_at)
        self.assertEqual(original,self.flow.motion_t0)
        self.assertLess(abs(self.flow.position()-x),1)

    def test_late_result_resumes_without_jumping(self):
        self.flow.motion_t0-=30
        self.flow.permit_pass()
        self.assertLess(abs(self.flow.position()-780),1)
        self.flow.release_at-=1
        self.assertGreater(self.flow.position(),900)

    def test_adopted_old_tile_can_leave_review_position(self):
        self.flow.motion_t0=None
        self.flow.permit_pass();self.flow.release_at-=1
        self.assertGreater(self.flow.position(),900)


if __name__=='__main__':unittest.main()
