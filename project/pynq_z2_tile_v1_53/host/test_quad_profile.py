import json,tempfile,unittest
from pathlib import Path
from tcp_transport import EventTCP
from workstation import Bridge,EthernetBridge,Station,ROOT
import recipes
import test_events as fixtures

class QuadProfileTests(unittest.TestCase):
 def test_request_flags_preserve_old_modes_and_add_quad(self):
  c=EventTCP('127.0.0.1');calls=[]
  c.exchange=lambda *args:(calls.append(args) or (b'',[],[]))
  for compression in (False,True):
   c.compression=compression
   for enhance,passes,mode in ((False,2,1),(True,2,0),(True,4,4)):
    c.capture(90,enhance,passes);self.assertEqual(calls[-1],(1,90,mode|(2 if compression else 0)))
    c.configure(90,enhance,passes);self.assertEqual(calls[-1],(5,90,mode))
 def test_wide_weak_request_is_bit32_and_requires_v152(self):
  c=EventTCP('127.0.0.1');calls=[];c.exchange=lambda *args:(calls.append(args) or (b'',[],[]));c.peer_version=0x12b00;c.compression=False
  c.capture(90,True,4,wide_weak=True);self.assertEqual(calls[-1],(1,90,4|32))
  c.configure(90,True,4,wide_weak=True);self.assertEqual(calls[-1],(5,90,4|32))
  c.peer_version=0x12a00
  with self.assertRaises(ValueError):c.capture(90,True,4,wide_weak=True)
  with self.assertRaises(ValueError):c.configure(90,True,4,wide_weak=True)
 def test_invalid_mode_does_not_send_request(self):
  c=EventTCP('127.0.0.1');calls=[];c.exchange=lambda *a:calls.append(a)
  for enhance,passes in ((True,3),(True,True),(False,4),(1,2)):
   with self.assertRaises(ValueError):c.capture(90,enhance,passes)
   with self.assertRaises(ValueError):c.configure(90,enhance,passes)
  self.assertEqual(calls,[])
 def quad(self):
  raw,d,m=fixtures.packet();d[7]|=3<<24;m[1]=0x11800;return raw,d,m
 def test_four_pass_decision_is_labeled_from_captured_config(self):
  raw,d,m=self.quad();f,_,_=Bridge.decode_event(raw,d,m,1)
  self.assertEqual(f['algorithm'],'FPGA_VALLEY17_HYST4_SUPPORT3_GRID32')
  applied=recipes.evidence(f,[]);self.assertEqual(applied['weak_passes'],4)
 def test_legacy_version_cannot_claim_quad(self):
  raw,d,m=self.quad();m[1]=0x11700
  with self.assertRaisesRegex(ValueError,'mode/version'):Bridge.decode_event(raw,d,m,1)
 def test_quad_flag_without_growth_is_invalid(self):
  raw,d,m=self.quad();d[7]&=~(1<<24)
  with self.assertRaisesRegex(ValueError,'mode/version'):Bridge.decode_event(raw,d,m,1)
 def test_wide_flag_is_labeled_and_versioned(self):
  raw,d,m=self.quad();d[7]|=1<<27;m[1]=0x12b00
  f,_,_=Bridge.decode_event(raw,d,m,1);self.assertEqual(f['algorithm'],'FPGA_DUALSCALE_VALLEY17_R16_HYST4_SUPPORT3_GRID32')
  m[1]=0x12a00
  with self.assertRaisesRegex(ValueError,'Wide weak'):Bridge.decode_event(raw,d,m,1)
 def test_equal_threshold_recipe_requires_pass_count_match(self):
  catalog=[dict(id='old',name='old',threshold=90,sha256='a',requires_weak_support=True),dict(id='quad',name='quad',threshold=90,sha256='b',requires_weak_support=True,weak_passes=4)]
  for mode,name,count in ((1,'old',2),(3,'quad',4)):
   f={'config_word':(mode<<24)|(90<<8)};a=recipes.evidence(f,catalog)
   self.assertEqual(a['recipe_id'],name);self.assertEqual(a['weak_passes'],count)
  self.assertEqual(recipes.evidence({'config_word':(3<<24)|(90<<8)},catalog[:1])['recipe_id'],'custom_or_unknown')
 def test_wide_recipe_identity_uses_captured_scale(self):
  catalog=[dict(id='narrow',name='narrow',threshold=90,sha256='a',requires_weak_support=True,weak_passes=4),dict(id='wide',name='wide',threshold=90,sha256='b',requires_weak_support=True,weak_passes=4,wide_weak=True)]
  self.assertEqual(recipes.evidence({'config_word':(3<<24)|(90<<8)},catalog)['recipe_id'],'narrow')
  self.assertEqual(recipes.evidence({'config_word':(3<<24)|(90<<8)|(1<<27)},catalog)['recipe_id'],'wide')
 def test_wide_recipe_refuses_legacy_firmware_then_sets_complete_request(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'host';p.mkdir();(p/'recipes.json').write_bytes((ROOT/'host/recipes.json').read_bytes())
   bridge=EthernetBridge('127.0.0.1');s=Station(t,bridge)
   try:
    old=(s.recipe_id,s.threshold,bridge.enhance,bridge.passes,bridge.low_gate,bridge.wide_weak)
    s.board_stats={'version':0x12a00}
    with self.assertRaisesRegex(ValueError,'V1.52'):s.action(dict(op='recipe',value='mvtec_hdmi_wide_weak_v152'))
    self.assertEqual(old,(s.recipe_id,s.threshold,bridge.enhance,bridge.passes,bridge.low_gate,bridge.wide_weak))
    s.board_stats={'version':0x12b00};s.action(dict(op='recipe',value='mvtec_hdmi_wide_weak_v152'))
    self.assertEqual((s.recipe_id,s.threshold,bridge.enhance,bridge.passes,bridge.wide_weak),
                     ('mvtec_hdmi_wide_weak_v152',90,True,4,True))
    snap=bridge.request_parameters(90);self.assertTrue(snap.wide_weak)
    s.action(dict(op='recipe',value='mvtec_hdmi_weak_v124'));self.assertFalse(bridge.wide_weak)
   finally:s.exit=True;s.worker.join(2);s.records.db.close();bridge.close()
 def test_invalid_pass_count_recipe_is_rejected(self):
  for changes in (dict(weak_passes=3),dict(weak_passes=True),dict(weak_passes=4,requires_weak_support=False)):
   with tempfile.TemporaryDirectory() as t:
    p=Path(t)/'host';p.mkdir();r=dict(id='bad',threshold=90,requires_weak_support=True);r.update(changes)
    (p/'recipes.json').write_text(json.dumps(dict(recipes=[r])))
    with self.assertRaises(ValueError):recipes.load(t)
 def test_real_catalog_sets_new_default_but_can_return_to_legacy(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'host';p.mkdir();(p/'recipes.json').write_bytes((ROOT/'host/recipes.json').read_bytes())
   bridge=EthernetBridge('127.0.0.1');s=Station(t,bridge)
   try:
    self.assertEqual((s.recipe_id,s.threshold,bridge.passes),('mvtec_hdmi_weak_v124',90,4))
    s.action(dict(op='recipe',value='mvtec_hdmi_weak_v16'));self.assertEqual((s.threshold,bridge.passes,bridge.enhance),(89,2,True))
    s.action(dict(op='recipe',value='mvtec_hdmi_baseline_v16'));self.assertEqual((bridge.passes,bridge.enhance),(2,False))
   finally:s.exit=True;s.worker.join(2);s.records.db.close();bridge.close()
 def test_jtag_does_not_claim_to_request_unsupported_quad_mode(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'host';p.mkdir();(p/'recipes.json').write_bytes((ROOT/'host/recipes.json').read_bytes())
   bridge=Bridge(t);s=Station(t,bridge)
   try:
    self.assertEqual((s.recipe_id,s.threshold),('mvtec_hdmi_weak_v16',89))
    with self.assertRaisesRegex(ValueError,'以太网'):
     s.action(dict(op='recipe',value='mvtec_hdmi_weak_v124'))
    self.assertEqual((s.recipe_id,s.threshold),('mvtec_hdmi_weak_v16',89))
    self.assertIsNone(bridge.proc)
   finally:s.exit=True;s.worker.join(2);s.records.db.close();bridge.close()

if __name__=='__main__':unittest.main(verbosity=2)
