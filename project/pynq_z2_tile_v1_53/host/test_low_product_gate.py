"""Explicit dark-material gate: protocol safety, captured provenance and defaults.

All sockets are loopback fixtures; no board or live workstation is contacted.
"""
import json
import socket
import struct
import tempfile
import threading
import time
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

import recipes
import test_events
from tcp_transport import EventTCP, MAGIC, FRAME_BYTES, LOW_GATE_VERSION
from workstation import Bridge, EthernetBridge, Records, ROOT, Station


def reply(op=3, version=LOW_GATE_VERSION, identity=0x54494c33):
    meta=[0]*24;meta[0]=identity;meta[1]=version
    payload=bytes(FRAME_BYTES) if op==1 else b''
    meta[3]=zlib.crc32(payload) if payload else 0
    flags=15 if payload else 5
    header=struct.pack('<68I',MAGIC,0 if payload else 1,len(payload),flags,*([0]*40),*meta)
    return header+struct.pack('<I',zlib.crc32(header))+payload


class LowGateTests(unittest.TestCase):
    def server(self,connections):
        """Per connection [(expected_op,response),...]; no board/network side effects."""
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(3)
        requests=[];errors=[]
        def serve():
            try:
                for index,steps in enumerate(connections):
                    conn,_=listener.accept();conn.settimeout(3)
                    with conn:
                        for expected,response in steps:
                            data=bytearray()
                            while len(data)<16:
                                part=conn.recv(16-len(data))
                                if not part:raise AssertionError('Client closed before expected request')
                                data.extend(part)
                            request=struct.unpack('<4I',data);requests.append((index,request))
                            if request[0]!=MAGIC or request[1]!=expected:
                                raise AssertionError('Unexpected request '+repr(request))
                            conn.sendall(response)
            except Exception as error:errors.append(error)
            finally:listener.close()
        worker=threading.Thread(target=serve,daemon=True);worker.start()
        client=EventTCP('127.0.0.1',listener.getsockname()[1])
        def finish():
            client.close();worker.join(4)
            self.assertFalse(worker.is_alive(),'Fixture server did not terminate')
            self.assertEqual(errors,[])
        self.addCleanup(finish)
        return client,requests

    def test_each_low_gate_request_probes_the_same_socket(self):
        c,requests=self.server([[(3,reply()),(5,reply()),(3,reply()),(1,reply(1))]])
        c.configure(36,low_gate=True)
        raw,*_=c.capture(36,low_gate=True)
        self.assertEqual(len(raw),FRAME_BYTES)
        self.assertEqual(requests,[(0,(MAGIC,3,0,0)),(0,(MAGIC,5,36,16)),
                                   (0,(MAGIC,3,0,0)),(0,(MAGIC,1,36,18))])

    def test_old_or_unknown_identity_rejected_before_low_request_despite_cached_version(self):
        for operation in ('capture','configure'):
            for version,identity in ((0x12400,0x54494c33),(0x12500,0)):
                with self.subTest(operation=operation,version=version,identity=identity):
                    c,requests=self.server([[(3,reply(version=version,identity=identity))]])
                    c.peer_version=0x12500
                    with self.assertRaisesRegex(ValueError,'requires firmware'):
                        getattr(c,operation)(36,low_gate=True)
                    self.assertIsNone(c.sock)
                    self.assertEqual(requests,[(0,(MAGIC,3,0,0))])

    def test_retry_checks_new_connection_before_resending_capture(self):
        partial=reply(1)[:340]
        c,requests=self.server([[(3,reply()),(1,partial)],[(3,reply()),(1,reply(1))]])
        raw,*_=c.capture(36,low_gate=True)
        self.assertEqual(len(raw),FRAME_BYTES)
        self.assertEqual([(i,r[1]) for i,r in requests],[(0,3),(0,1),(1,3),(1,1)])
        self.assertEqual(c.reconnects,1)

    def test_retry_to_older_firmware_never_sends_unsupported_capture_or_ack(self):
        c,requests=self.server([[(3,reply()),(1,reply(1)[:340])],[(3,reply(version=0x12400))]])
        with self.assertRaisesRegex(ValueError,'requires firmware'):c.capture(36,low_gate=True)
        self.assertEqual([(i,r[1]) for i,r in requests],[(0,3),(0,1),(1,3)])
        self.assertIsNone(c.sock)

    def test_broken_preflight_retries_read_only_probe_before_configure(self):
        c,requests=self.server([[(3,b'broken')],[(3,reply()),(5,reply())]])
        c.configure(36,low_gate=True)
        self.assertEqual([(i,r[1]) for i,r in requests],[(0,3),(1,3),(1,5)])

    def test_corrupt_preflight_crc_never_changes_configuration(self):
        response=bytearray(reply());response[272]^=1
        c,requests=self.server([[(3,response)]])
        with self.assertRaisesRegex(ValueError,'Header CRC'):c.configure(36,low_gate=True)
        self.assertEqual([r[1] for _,r in requests],[3]);self.assertEqual(c.reconnects,0)

    def test_default_mode_adds_no_preflight(self):
        c,requests=self.server([[(5,reply()),(1,reply(1))]])
        c.configure(90,passes=4);c.capture(90,passes=4)
        self.assertEqual(requests,[(0,(MAGIC,5,90,4)),(0,(MAGIC,1,90,6))])

    def test_flags_are_orthogonal_and_boolean_is_strict(self):
        c=EventTCP('127.0.0.1');c.peer_version=0x12500;calls=[]
        c.exchange=lambda *args:(calls.append(args) or (b'',[],[]))
        for low in (False,True):
            for compression in (False,True):
                for packed in (False,True):
                    c.compression=compression;c.packed=packed
                    for enhance,passes,mode in ((False,2,1),(True,2,0),(True,4,4)):
                        c.capture(36,enhance,passes,low)
                        self.assertEqual(calls[-1],(1,36,mode|(16 if low else 0)|(2 if compression else 0)|(8 if packed and compression else 0)))
                        c.configure(36,enhance,passes,low)
                        self.assertEqual(calls[-1],(5,36,mode|(16 if low else 0)))
        calls.clear()
        for invalid in (0,1,None,'true',[],{}):
            with self.assertRaises(ValueError):c.capture(36,low_gate=invalid)
            with self.assertRaises(ValueError):c.configure(36,low_gate=invalid)
        self.assertEqual(calls,[])

    def catalog_station(self,ethernet=True):
        temporary=tempfile.TemporaryDirectory(prefix='tile_low_gate_');root=Path(temporary.name)
        (root/'host').mkdir();(root/'host/recipes.json').write_bytes((ROOT/'host/recipes.json').read_bytes())
        bridge=EthernetBridge('127.0.0.1') if ethernet else Bridge(root)
        station=Station(root,bridge)
        def finish():
            station.exit=True;station.worker.join(3);self.assertFalse(station.worker.is_alive())
            station.records.db.close();bridge.close();temporary.cleanup()
        self.addCleanup(finish)
        return station,bridge

    def test_recipe_preflight_is_local_and_failure_preserves_requested_settings(self):
        s,b=self.catalog_station()
        self.assertEqual((s.recipe_id,s.threshold,b.passes,b.low_gate),('mvtec_hdmi_weak_v124',90,4,False))
        before=(s.recipe_id,s.threshold,b.passes,b.enhance,b.low_gate)
        with patch.object(b.transport,'exchange',side_effect=AssertionError('UI must not use socket')):
            for version in (None,0,0x12400,True):
                s.board_stats={} if version is None else {'version':version}
                with self.assertRaisesRegex(ValueError,'V1.37'):
                    s.action(dict(op='recipe',value='synthetic_dark_v137'))
                self.assertEqual((s.recipe_id,s.threshold,b.passes,b.enhance,b.low_gate),before)
            s.board_stats={'version':0x12500};s.busy=True
            s.action(dict(op='recipe',value='synthetic_dark_v137'))
            self.assertEqual((s.recipe_id,s.threshold,b.passes,b.enhance,b.low_gate),('synthetic_dark_v137',36,2,True,True))
            self.assertTrue(s.state()['requested_low_gate'])
            s.action(dict(op='threshold',value=37));self.assertTrue(b.low_gate)
            s.action(dict(op='recipe',value='synthetic_v16'));self.assertFalse(b.low_gate)
            s.busy=False

    def test_jtag_rejects_low_gate_without_starting_or_mutating(self):
        s,b=self.catalog_station(False);before=(s.recipe_id,s.threshold)
        s.board_stats={'version':0x12500}
        with self.assertRaisesRegex(ValueError,'以太网'):
            s.action(dict(op='recipe',value='synthetic_dark_v137'))
        self.assertEqual((s.recipe_id,s.threshold),before);self.assertIsNone(b.proc)

    def test_worker_rechecks_cached_capability_and_does_not_save_or_ack_unsupported_board(self):
        c,requests=self.server([[(3,reply(version=0x12400))]])
        s,b=self.catalog_station();b.transport=c;b.check_capture_health=False
        s.board_stats={'version':0x12500}
        s.action(dict(op='recipe',value='synthetic_dark_v137'))
        s.action(dict(op='capture'))
        deadline=time.monotonic()+3
        while not s.error and time.monotonic()<deadline:time.sleep(.01)
        self.assertIn('requires firmware',s.error)
        self.assertEqual(requests,[(0,(MAGIC,3,0,0))])
        self.assertEqual(s.records.all(),[]);self.assertIsNone(s.records.confirmations.pending())
        self.assertIsNone(s.pending_ack);self.assertFalse(s.enabled)

    def test_bridge_forwards_gate_on_both_operations(self):
        b=EthernetBridge('127.0.0.1');b.low_gate=True;b.passes=4
        with patch.object(b.transport,'capture',return_value=(*test_events.packet(),1)) as capture:
            b.capture(90);capture.assert_called_once_with(90,enhance=True,passes=4,low_gate=True)
        with patch.object(b.transport,'configure') as configure:
            b.configure(90);configure.assert_called_once_with(90,enhance=True,passes=4,low_gate=True)

    def test_captured_gate_and_version_control_attribution_and_survive_archive(self):
        catalog=recipes.load(ROOT)
        for low,identity in ((False,'synthetic_v16'),(True,'synthetic_dark_v137')):
            raw,d,m=test_events.packet();m[1]=0x12500;d[7]|=1<<24
            if low:d[7]|=1<<26
            frame,img,mask=Bridge.decode_event(raw,d,m,1);frame.update(recipes.evidence(frame,catalog))
            self.assertEqual(frame['recipe_id'],identity)
            self.assertEqual(frame['low_gate_enabled'],low);self.assertEqual(frame['applied_product_gate_sum'],160 if low else 320)
            with tempfile.TemporaryDirectory(prefix='tile_gate_evidence_') as root:
                records=Records(root)
                try:
                    key=records.save(frame,img,mask,'hardware_alarm');saved=records.get(key)
                    self.assertEqual(saved['recipe_id'],identity);self.assertEqual(saved['low_gate_enabled'],low)
                    self.assertEqual(saved['applied_product_gate_sum'],frame['applied_product_gate_sum'])
                finally:records.db.close()
        m[1]=0x12400
        with self.assertRaisesRegex(ValueError,'Low product gate.*version'):Bridge.decode_event(raw,d,m,1)
        only_old=[r for r in catalog if r['id']!='synthetic_dark_v137']
        self.assertEqual(recipes.evidence({'config_word':d[7]},only_old)['recipe_id'],'custom_or_unknown')

    def test_legacy_recipe_hashes_and_default_are_unchanged(self):
        # Frozen V1.36 recipe hashes: no dependency on an old installation.
        old={'synthetic_v16':'0fe8a2a197a674d6dcbb431f5f806b357246d2e9a9db0552e59b13b168ac9115',
             'mvtec_hdmi_weak_v124':'9f38669978c64e85f9bcb67037a4fe66a4ed08e5bef2ce17dd5b8ed96fb62007',
             'mvtec_hdmi_weak_v16':'811e9c1865e4231a85770e4c2358e0f9056b17734065ea4a2102a875aea1dbed',
             'mvtec_hdmi_baseline_v16':'abeec308b94510fb838393c504853a2daed01f6d0e2dddadff9b842ec6e0032b'}
        new=json.loads((ROOT/'host/recipes.json').read_text(encoding='utf-8'))
        current={r['id']:r for r in recipes.load(ROOT)}
        self.assertEqual(new['default'],'mvtec_hdmi_weak_v124')
        for identity,expected in old.items():self.assertEqual(current[identity]['sha256'],expected)

    def test_recipe_gate_field_is_strict_boolean(self):
        for low in (0,1,None,'false'):
            with tempfile.TemporaryDirectory(prefix='tile_gate_recipe_') as root:
                p=Path(root)/'host';p.mkdir()
                (p/'recipes.json').write_text(json.dumps(dict(recipes=[dict(id='bad',threshold=36,low_gate=low)])))
                with self.assertRaisesRegex(ValueError,'product gate'):recipes.load(root)


if __name__=='__main__':unittest.main(verbosity=2)
