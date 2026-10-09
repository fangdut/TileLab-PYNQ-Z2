import unittest
from render_progress import RenderProgress

class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.tracker=RenderProgress();self.p=dict(phase='rendering',source='real_video',player_session='a'*32,request_id='b'*32,drawn_frames=100,drawn_source_frame=100)
    def observe(self,now,**changes):self.p.update(changes);return self.tracker.observe(self.p,now)
    def moving(self):self.observe(10);return self.observe(10.1,drawn_frames=106,drawn_source_frame=106)
    def test_first_report_waits_for_actual_change(self):self.assertEqual(self.observe(10)['state'],'WAITING')
    def test_draw_count_and_source_advance_confirms(self):self.assertTrue(self.moving()['progressing'])
    def test_fresh_status_without_drawing_stalls(self):
        self.moving();self.assertEqual(self.observe(11.101,utc='fresh')['state'],'STALLED')
    def test_timer_or_animation_position_is_not_drawing(self):
        self.observe(10);self.assertEqual(self.observe(11.1,rendered_frames=9999,position_seconds=100)['state'],'STALLED')
    def test_same_source_redraw_does_not_claim_movement(self):
        self.observe(10);self.assertEqual(self.observe(11.1,drawn_frames=999)['state'],'STALLED')
    def test_source_without_new_draw_does_not_claim_movement(self):
        self.observe(10);self.assertEqual(self.observe(11.1,drawn_source_frame=200)['state'],'STALLED')
    def test_frame_code_wrap_is_valid_progress(self):
        self.observe(10,drawn_source_frame=719);self.assertTrue(self.observe(10.1,drawn_frames=101,drawn_source_frame=0)['progressing'])
    def test_counter_reset_requires_new_change(self):
        self.moving();self.assertEqual(self.observe(10.2,drawn_frames=0,drawn_source_frame=0)['state'],'COUNTER_RESET')
        self.assertTrue(self.observe(10.3,drawn_frames=6,drawn_source_frame=6)['progressing'])
    def test_same_name_request_does_not_restart_stall_grace(self):
        self.moving();self.assertEqual(self.observe(11.101,request_id='c'*32)['state'],'STALLED')
    def test_new_session_starts_fresh_observation(self):
        self.moving();self.assertEqual(self.observe(11.2,player_session='c'*32)['state'],'WAITING')
    def test_new_source_starts_fresh_observation(self):
        self.moving();self.assertEqual(self.observe(11.2,source='fast')['state'],'WAITING')
    def test_static_is_exempt(self):self.assertEqual(self.observe(10,phase='static',source='station_0')['state'],'NOT_REQUIRED')
    def test_media_player_has_no_false_drawing_claim(self):
        self.assertEqual(self.observe(10,phase='playing',source='burst')['state'],'UNOBSERVED')
    def test_invalid_counter_metadata(self):
        for key,value in [('drawn_frames',True),('drawn_frames',-1),('drawn_frames',None),('drawn_source_frame',720),('drawn_source_frame',-1),('drawn_source_frame',False)]:
            p=dict(self.p);p[key]=value;self.assertEqual(self.tracker.observe(p,10)['state'],'INVALID')
    def test_fast_sources_check_their_own_period(self):
        self.assertEqual(self.observe(10,source='ultrafast',drawn_source_frame=180)['state'],'INVALID')
    def test_observation_gap_is_not_evidence_of_stall(self):
        self.moving();self.assertEqual(self.observe(20)['state'],'WAITING')
    def test_clock_backwards_restarts_observation(self):
        self.moving();self.assertEqual(self.observe(9)['state'],'WAITING')
    def test_nonfinite_clock_is_unconfirmed(self):
        for now in (float('nan'),float('inf')):self.assertEqual(self.observe(now)['state'],'CLOCK_UNCERTAIN')
    def test_stall_boundary_and_recovery(self):
        self.moving();self.assertEqual(self.observe(11.1)['state'],'PROGRESSING')
        self.assertEqual(self.observe(11.100001)['state'],'STALLED')
        self.assertTrue(self.observe(11.2,drawn_frames=107,drawn_source_frame=107)['progressing'])
    def test_frequent_polling_does_not_fake_progress(self):
        self.observe(10)
        for n in range(1,111):result=self.observe(10+n*.01)
        self.assertEqual(result['state'],'STALLED')

if __name__=='__main__':unittest.main()
