"""Logical-request deadlines with actual parsers and a deterministic socket clock.

No real sockets, board, or old project imports. The fake OS honours each socket
timeout; minutes of positive slow progress therefore require no real sleeps.
Station cases really persist evidence in independent temporary directories.
"""
from contextlib import ExitStack
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile
import threading
import time as wall_clock
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib

import tcp_transport
from tcp_transport import EventTCP,MAGIC,FRAME_BYTES
from workstation import EthernetBridge,ROOT,Station
import test_events

OBSERVATIONS=[]


class Clock:
    def __init__(self):self.now=0.;self.sleeps=[]
    def monotonic(self):return self.now
    def perf_counter(self):return self.now
    def time(self):return 1_800_000_000+self.now
    def sleep(self,value):self.sleeps.append(value);self.now+=value


class Peer:
    def __init__(self,clock,plans):
        self.clock=clock;self.plans=list(plans);self.sockets=[];self.requests=[];self.acked=False
        self.entered=threading.Event();self.release=threading.Event();self.gate_op=None;self.gate_at=0;self.gated=False
    def create(self,*args):
        if not self.plans:raise AssertionError('Unexpected extra connection; no real socket is allowed')
        sock=Socket(self,self.plans.pop(0));self.sockets.append(sock);return sock
    def packet(self,request,step):
        _,op,a,b=request;meta=[0]*24;meta[:3]=[0x54494c33,0x12500,7]
        if op==1:
            raw,d,_=test_events.packet();d[8]=3
            d[7]=0x00f30007|(a<<8)|(int(not(b&1))<<24)|(int(bool(b&4))<<25)|(int(bool(b&16))<<26)
            flags=15;payload=raw
            if step.get('rle'):
                raw=bytes(FRAME_BYTES);payload=struct.pack('<2I',0x80000000|FRAME_BYTES//4,0);flags|=256
            meta[3]=zlib.crc32(raw)^int(bool(step.get('bad_pixel_crc')));meta[6]=1;meta[18]=60
        else:
            assert op in (2,3,4,5),op
            if op==2:
                assert (a,b)==(7,1);self.acked=True
            payload=b'';d=[0]*40;flags=5
            d[:6]=[0x484c5431,1,0,0,0,1]
            d[23:37]=[0x52454331,0,0,0,0,0,0,0,0,0,3,1000,3000,0]
            meta[4]=int(self.acked);meta[6]=int(not self.acked);meta[18]=60
        header=struct.pack('<68I',MAGIC,0 if op==1 else 1,len(payload),flags,*d,*meta)
        return header+struct.pack('<I',zlib.crc32(header)^int(bool(step.get('bad_header_crc'))))+payload


class Socket:
    def __init__(self,peer,plan):
        self.peer=peer;self.plan=plan;self.steps=list(plan.get('steps',[]));self.timeout=None
        self.closed=False;self.offset=0;self.buffer=b'';self.step={};self.operation=None
        self.timeouts=[];self.waits=[];self.connected=False
    def setsockopt(self,*args):pass
    def settimeout(self,value):self.timeout=value;self.timeouts.append(value)
    def wait(self,seconds,stage):
        assert self.timeout is not None and self.timeout>0
        self.waits.append(dict(stage=stage,at=self.peer.clock.now,requested_wait=seconds,timeout=self.timeout))
        if seconds>self.timeout:
            self.peer.clock.now+=self.timeout
            raise TimeoutError('Injected socket idle/remaining-budget timeout')
        self.peer.clock.now+=seconds
    def connect(self,address):
        assert address[0]=='127.0.0.1';self.wait(self.plan.get('connect_delay',0),'connect');self.connected=True
    def sendall(self,data):
        request=struct.unpack('<4I',data);assert request[0]==MAGIC
        self.operation=request[1];self.peer.requests.append(request)
        self.step=self.steps.pop(0) if self.steps else {}
        if 'op' in self.step:assert self.step['op']==self.operation
        self.wait(self.step.get('send_delay',0),'send')
        self.buffer=self.peer.packet(request,self.step);self.offset=0
    def recv_into(self,view,n):
        assert not self.closed
        if self.offset>=self.step.get('error_after',math.inf):raise ConnectionResetError('Injected reset after progress')
        header=self.offset<276
        delay=self.step.get('header_delay' if header else 'payload_delay',self.step.get('delay',.001))
        chunk=self.step.get('header_chunk' if header else 'payload_chunk',self.step.get('chunk',65536))
        if self.peer.gate_op==self.operation and not self.peer.gated and self.peer.clock.now>=self.peer.gate_at:
            self.peer.gated=True;self.peer.entered.set()
            if not self.peer.release.wait(4):raise TimeoutError('Test barrier not released')
        self.wait(delay,'header' if header else 'payload')
        count=min(n,len(view),chunk,len(self.buffer)-self.offset);assert count>0
        view[:count]=self.buffer[self.offset:self.offset+count];self.offset+=count;return count
    def close(self):self.closed=True


class DeadlineTests(unittest.TestCase):
    def setup_client(self,plans,preconnected=False,first_frame=False,**kwargs):
        clock=Clock();peer=Peer(clock,plans);client=EventTCP('127.0.0.1',**kwargs)
        stack=ExitStack();stack.enter_context(patch.object(tcp_transport,'time',clock))
        stack.enter_context(patch.object(tcp_transport.socket,'socket',side_effect=peer.create))
        if preconnected:client.sock=peer.create();client.first_frame=first_frame
        def finish():peer.release.set();client.close();stack.close()
        self.addCleanup(finish)
        return client,peer,clock

    def exhausted(self,client,peer,clock,call,limit):
        with self.assertRaises(tcp_transport.RequestDeadlineExceeded):call()
        self.assertAlmostEqual(clock.now,limit,places=6)
        self.assertIsNone(client.sock);self.assertIsNone(client._request_deadline)
        self.assertTrue(all(sock.closed for sock in peer.sockets))
        self.assertTrue(client.failures)
        OBSERVATIONS.append(dict(test=self._testMethodName,virtual_seconds=clock.now,
                                 requests=[list(request) for request in peer.requests],connections=len(peer.sockets)))

    def test_time_budget_validation_and_legacy_positional_arguments(self):
        client=EventTCP('127.0.0.1',9133,.35,True,False)
        self.assertEqual(client.control_timeout,3.0);self.assertEqual(client.image_timeout,8.0)
        for name in ('control_timeout','image_timeout'):
            for value in (0,-1,float('inf'),float('nan'),True,False,None,'3'):
                with self.subTest(name=name,value=value),self.assertRaises(ValueError):EventTCP('127.0.0.1',**{name:value})
        EventTCP('127.0.0.1',control_timeout=.05,image_timeout=.1)

    def test_slow_header_progress_expires_and_recv_timeout_shrinks(self):
        client,peer,clock=self.setup_client([dict(steps=[dict(op=3,chunk=1,delay=.34)])],preconnected=True)
        self.exhausted(client,peer,clock,client.stats,3)
        self.assertEqual(len(peer.requests),1);self.assertEqual(client.reconnects,0)
        self.assertLess(peer.sockets[0].waits[-1]['timeout'],.35)
        self.assertGreater(client.total_received_bytes,0);self.assertLess(client.total_received_bytes,272)

    def test_slow_steady_payload_progress_expires_before_full_frame(self):
        client,peer,clock=self.setup_client([dict(steps=[dict(op=1,payload_chunk=1024,payload_delay=.34)])],preconnected=True)
        self.exhausted(client,peer,clock,lambda:client.capture(36),8)
        self.assertEqual(client.stage,'payload');self.assertGreater(client.total_received_bytes,276)
        self.assertLess(client.total_received_bytes,FRAME_BYTES);self.assertFalse(peer.acked)

    def test_slow_first_frame_keeps_2_second_idle_inside_8_second_total(self):
        client,peer,clock=self.setup_client([dict(steps=[dict(op=1,delay=1.9)])],preconnected=True,first_frame=True)
        self.exhausted(client,peer,clock,lambda:client.capture(36),8)
        waits=peer.sockets[0].waits
        self.assertTrue(any(item['timeout']==2 for item in waits));self.assertLess(waits[-1]['timeout'],2)

    def test_connect_timeout_and_retry_share_control_budget(self):
        client,peer,clock=self.setup_client([dict(connect_delay=3),dict(connect_delay=3)])
        self.exhausted(client,peer,clock,client.stats,3)
        self.assertEqual(peer.requests,[]);self.assertEqual(len(peer.sockets),2)
        self.assertAlmostEqual(peer.sockets[0].waits[0]['timeout'],2)
        self.assertAlmostEqual(peer.sockets[1].waits[0]['timeout'],.95)

    def test_low_gate_preflight_and_blocked_send_share_control_budget(self):
        plan=dict(connect_delay=1.9,steps=[dict(op=3,chunk=140,delay=.3),dict(op=5,send_delay=.25)])
        client,peer,clock=self.setup_client([plan])
        self.exhausted(client,peer,clock,lambda:client.configure(36,low_gate=True),3)
        self.assertEqual([request[1] for request in peer.requests],[3,5])
        self.assertEqual(peer.sockets[0].waits[-1]['stage'],'send')
        self.assertAlmostEqual(peer.sockets[0].waits[-1]['timeout'],.2)

    def test_retry_after_partial_header_does_not_reset_deadline(self):
        plans=[dict(steps=[dict(op=3,chunk=16,delay=.3,error_after=96)]),dict(steps=[dict(op=3,chunk=1,delay=.3)])]
        client,peer,clock=self.setup_client(plans,preconnected=True)
        self.exhausted(client,peer,clock,client.stats,3)
        self.assertEqual([request[1] for request in peer.requests],[3,3]);self.assertEqual(client.reconnects,1)
        self.assertAlmostEqual(clock.sleeps[0],.05)

    def test_short_remaining_budget_expires_in_backoff_without_second_socket(self):
        client,peer,clock=self.setup_client([dict(steps=[dict(op=3,error_after=0)])],preconnected=True,control_timeout=.03)
        self.exhausted(client,peer,clock,client.stats,.03)
        self.assertEqual(len(peer.sockets),1);self.assertEqual(len(peer.requests),1)
        self.assertEqual(clock.sleeps,[.03])

    def test_custom_capture_budget_caps_initial_idle_allowance(self):
        client,peer,clock=self.setup_client([dict(steps=[dict(op=1,delay=.2)])],preconnected=True,first_frame=True,image_timeout=.1)
        self.exhausted(client,peer,clock,lambda:client.capture(36),.1)
        self.assertAlmostEqual(peer.sockets[0].waits[-1]['timeout'],.1)

    def test_capture_preflight_uses_parent_8_second_budget_not_new_3_second_budget(self):
        steps=[dict(op=3,chunk=16,delay=.3),dict(op=1,payload_chunk=1024,payload_delay=.3)]
        client,peer,clock=self.setup_client([dict(steps=steps)],preconnected=True)
        self.exhausted(client,peer,clock,lambda:client.capture(36,low_gate=True),8)
        self.assertEqual([request[1] for request in peer.requests],[3,1])
        self.assertEqual(client.stage,'payload');self.assertEqual(client.reconnects,0)

    def test_retry_repeats_capability_probe_without_resetting_capture_budget(self):
        first=[dict(op=3,delay=.34),dict(op=1,chunk=64,delay=.34,error_after=340)]
        second=[dict(op=3,delay=.34),dict(op=1,payload_chunk=1024,payload_delay=.34)]
        client,peer,clock=self.setup_client([dict(steps=first),dict(steps=second)],preconnected=True)
        self.exhausted(client,peer,clock,lambda:client.capture(36,low_gate=True),8)
        self.assertEqual([request[1] for request in peer.requests],[3,1,3,1]);self.assertEqual(client.reconnects,1)

    def test_normal_raw_capture_stats_and_ack_succeed_and_clear_scope(self):
        client,peer,clock=self.setup_client([dict(steps=[dict(op=1),dict(op=2),dict(op=3)])])
        raw,*_=client.capture(36);self.assertEqual(len(raw),FRAME_BYTES)
        self.assertTrue(all(client.last_timing[field] for field in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified')))
        self.assertIsNone(client._request_deadline)
        client.ack(7,1);self.assertTrue(peer.acked);self.assertEqual(client.stats()['head'],1)
        self.assertIsNone(client._request_deadline);self.assertLess(clock.now,1)
        self.assertEqual(client.reconnects,0)

    def test_idle_timeout_can_still_retry_successfully_inside_total_budget(self):
        plans=[dict(steps=[dict(op=3,delay=.5)]),dict(steps=[dict(op=3)])]
        client,peer,clock=self.setup_client(plans,preconnected=True)
        self.assertEqual(client.stats()['boot_id'],7);self.assertEqual(client.reconnects,1)
        self.assertLess(clock.now,3);self.assertIsNone(client._request_deadline)
        self.assertTrue(peer.sockets[0].closed);self.assertFalse(peer.sockets[1].closed)

    def test_invalid_header_or_pixel_crc_is_fatal_without_retry_or_ack(self):
        for field,expression in (('bad_header_crc','Header CRC'),('bad_pixel_crc','frame CRC')):
            with self.subTest(field=field):
                client,peer,clock=self.setup_client([dict(steps=[dict(op=1,**{field:True})])],preconnected=True)
                with self.assertRaisesRegex(ValueError,expression):client.capture(36)
                self.assertEqual(client.reconnects,0);self.assertIsNone(client.sock)
                self.assertIsNone(client._request_deadline);self.assertFalse(peer.acked)

    def test_rle_decode_over_budget_is_not_returned_as_success(self):
        client,peer,clock=self.setup_client([dict(steps=[dict(op=1,rle=True)])],preconnected=True)
        original=tcp_transport.decode_rle
        def slow_decode(*args):
            value=original(*args);clock.now+=9;return value
        with patch.object(tcp_transport,'decode_rle',slow_decode),self.assertRaises(tcp_transport.RequestDeadlineExceeded):client.capture(36)
        self.assertGreater(clock.now,8);self.assertIsNone(client.sock);self.assertIsNone(client._request_deadline)
        self.assertEqual(client.reconnects,0);self.assertFalse(peer.acked)

    def test_crc_failure_after_cpu_delay_remains_integrity_error(self):
        client,peer,clock=self.setup_client([dict(steps=[dict(op=1,bad_pixel_crc=True)])],preconnected=True)
        def slow_crc(data):
            if len(data)==FRAME_BYTES:clock.now+=9
            return zlib.crc32(data)
        with patch.object(tcp_transport,'zlib',SimpleNamespace(crc32=slow_crc)),self.assertRaisesRegex(ValueError,'frame CRC'):client.capture(36)
        self.assertGreater(clock.now,8);self.assertEqual(client.reconnects,0)
        self.assertIsNone(client.sock);self.assertIsNone(client._request_deadline);self.assertFalse(peer.acked)

    def test_valid_crc_completed_after_deadline_is_not_returned_as_success(self):
        client,peer,clock=self.setup_client([dict(steps=[dict(op=1)])],preconnected=True)
        def slow_crc(data):
            if len(data)==FRAME_BYTES:clock.now+=9
            return zlib.crc32(data)
        with patch.object(tcp_transport,'zlib',SimpleNamespace(crc32=slow_crc)),self.assertRaises(tcp_transport.RequestDeadlineExceeded):client.capture(36)
        self.assertGreater(clock.now,8);self.assertEqual(client.reconnects,0)
        self.assertIsNone(client.sock);self.assertIsNone(client._request_deadline);self.assertFalse(peer.acked)

    def station(self,client,peer):
        temporary=tempfile.TemporaryDirectory(prefix='tile_v140_deadline_');bridge=EthernetBridge('127.0.0.1')
        bridge.transport=client;bridge.check_capture_health=False;station=Station(temporary.name,bridge)
        def finish():
            peer.release.set();station.exit=True;station.worker.join(5);self.assertFalse(station.worker.is_alive())
            station.records.db.close();bridge.close();temporary.cleanup()
        self.addCleanup(finish);return station

    def until(self,predicate):
        end=wall_clock.monotonic()+4
        while not predicate():
            if wall_clock.monotonic()>end:self.fail('Station did not finish bounded operation')
            wall_clock.sleep(.005)

    def test_station_half_frame_timeout_after_pause_never_saves_or_acks(self):
        client,peer,clock=self.setup_client([dict(steps=[dict(op=1,payload_chunk=1024,payload_delay=.34)])],preconnected=True)
        peer.gate_op=1;peer.gate_at=1;station=self.station(client,peer)
        station.action(dict(op='capture'));self.assertTrue(peer.entered.wait(2))
        acquired=station.lock.acquire(blocking=False);self.assertTrue(acquired)
        if acquired:station.lock.release()
        station.action(dict(op='pause'));self.assertTrue(station.busy)
        peer.release.set();self.until(lambda:not station.busy)
        self.assertIn('deadline',station.error.lower());self.assertAlmostEqual(clock.now,8)
        self.assertEqual(station.captures,0);self.assertEqual(station.records.all(),[])
        self.assertFalse(list((Path(station.root)/'review_records').glob('*.png')))
        self.assertIsNone(station.pending_ack);self.assertIsNone(station.records.confirmations.pending())
        self.assertFalse(station.enabled or station.manual or station.retry_requested)
        self.assertFalse(peer.acked);self.assertEqual([request[1] for request in peer.requests],[1])

    def test_station_ack_reply_deadline_keeps_saved_identity_for_reconciliation(self):
        plans=[dict(steps=[dict(op=1),dict(op=2,chunk=1,delay=.34)]),dict(steps=[dict(op=3),dict(op=3)])]
        client,peer,clock=self.setup_client(plans,preconnected=True);peer.gate_op=2;peer.gate_at=1
        station=self.station(client,peer);station.action(dict(op='capture'));self.assertTrue(peer.entered.wait(2))
        before=station.records.all();self.assertEqual(len(before),1);identity=(before[0]['boot_id'],before[0]['event_id'])
        self.assertEqual(identity,(7,1));station.action(dict(op='pause'));peer.release.set()
        self.until(lambda:not station.busy)
        self.assertIn('deadline',station.error.lower());self.assertIsNone(client.sock)
        self.assertEqual((station.pending_ack['boot_id'],station.pending_ack['event_id']),identity)
        self.assertEqual(station.records.confirmations.pending()['frame']['event_id'],1)
        self.assertEqual(station.captures,1);self.assertEqual([request[1] for request in peer.requests],[1,2])
        station.action(dict(op='resume_pending'));self.until(lambda:not station.busy and not station.retry_requested)
        self.assertEqual(station.records.all(),before);self.assertIsNone(station.pending_ack)
        self.assertIsNone(station.records.confirmations.pending());self.assertEqual(station.captures,1)
        self.assertEqual([request[1] for request in peer.requests],[1,2,3,3])
        self.assertEqual(station.records.confirmations.history()[0]['status'],'ALREADY_ACKNOWLEDGED')


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(DeadlineTests);names=[test.id() for test in suite]
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    output=ROOT/'reports/v148';output.mkdir(parents=True,exist_ok=True)
    summary=dict(passed=result.wasSuccessful(),tests=result.testsRun,test_ids=names,
                 failures=len(result.failures),errors=len(result.errors),deadline_cases=OBSERVATIONS,
                 source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                for name in ('host/tcp_transport.py','host/workstation.py','host/test_request_deadline.py')},
                 scope='Actual EventTCP parsing/CRC and Station archive with deterministic per-recv socket clock; no real network/board.',
                 limitations=['Virtual times are injected test times, not measured physical throughput. CPU deadline checks detect completion overruns and do not preempt native decoders.'])
    (output/'deadline_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
