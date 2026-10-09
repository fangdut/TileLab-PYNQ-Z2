"""Deterministic recipe races with real Station/bridge code and no sockets.

Barriers stop before the bridge reads its settings, not after transport keyword
arguments were already evaluated. Full-sized transport fixtures are decoded and
manual evidence is really saved in a unique temporary directory. Frozen V1.37
methods below provide explicit negative controls; no old project is imported.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from recovery import TransientTransportError
from workstation import Bridge, EthernetBridge, ROOT, Station
import test_events

OLD=(90,True,4,False)
NEW=(36,True,2,True)
PROOFS=[]


class Transport:
    address='127.0.0.1'
    port=9133
    def __init__(self):
        self.calls=[];self.acks=[];self.last_timing={};self.force_captured=None
        self.lock=threading.Lock();self.next_event=1;self.hook=None;self.fail_once=False
    def record(self,operation,threshold,enhance,passes,low_gate):
        value=(threshold,enhance,passes,low_gate)
        with self.lock:self.calls.append((operation,value))
        if self.hook:self.hook(operation,value)
        if self.fail_once:
            self.fail_once=False;raise OSError('Injected transport failure')
        return value
    def configure(self,threshold,enhance=True,passes=2,low_gate=False):
        self.record('configure',threshold,enhance,passes,low_gate)
    def capture(self,threshold,enhance=True,passes=2,low_gate=False):
        value=self.record('capture',threshold,enhance,passes,low_gate)
        threshold,enhance,passes,low_gate=self.force_captured or value
        raw,descriptor,meta=test_events.packet();meta[1]=0x12500
        descriptor[7]=0x00f30007|(threshold<<8)|(int(enhance)<<24)|(int(enhance and passes==4)<<25)|(int(low_gate)<<26)
        descriptor[8]=3;descriptor[0]=self.next_event;descriptor[2]+=self.next_event
        self.next_event+=1
        return raw,descriptor,meta,1
    def ack(self,boot,event):self.acks.append((boot,event))
    def stats(self):return dict(version=0x12500,boot_id=7,head=self.acks[-1][1] if self.acks else 0,depth=0,frames=60)
    def close(self):pass


def legacy_configure(self,threshold):
    # Frozen V1.37 body: each flag is read after threshold was passed by caller.
    return self.call(self.transport.configure,threshold,enhance=self.enhance,passes=self.passes,low_gate=self.low_gate)


def legacy_capture(self,threshold):
    # Frozen V1.37 request construction. Decode is unchanged and irrelevant to
    # the negative-control race, but retained to exercise the complete method.
    packet=self.call(self.transport.capture,threshold,enhance=self.enhance,passes=self.passes,low_gate=self.low_gate)
    frame,image,mask=Bridge.decode_event(*packet)
    frame.update(transport='ETHERNET_TCP',**self.transport.last_timing)
    return frame,image,mask


class RecipeSnapshotTests(unittest.TestCase):
    def bridge(self):
        bridge=EthernetBridge('127.0.0.1');bridge.transport=Transport();bridge.check_capture_health=False
        return bridge

    def station(self):
        temporary=tempfile.TemporaryDirectory(prefix='tile_v138_recipe_snapshot_')
        root=Path(temporary.name);(root/'host').mkdir()
        (root/'host/recipes.json').write_bytes((ROOT/'host/recipes.json').read_bytes())
        bridge=self.bridge();station=Station(root,bridge);station.board_stats=bridge.transport.stats()
        releases=[]
        def finish():
            for event in releases:event.set()
            station.exit=True;station.worker.join(4)
            self.assertFalse(station.worker.is_alive(),'Fixture worker did not terminate')
            station.records.db.close();bridge.close();temporary.cleanup()
        self.addCleanup(finish)
        return station,bridge,releases

    def until(self,predicate,seconds=3):
        end=time.monotonic()+seconds
        while not predicate():
            if time.monotonic()>end:self.fail('Bounded fixture condition timed out')
            time.sleep(.005)

    def barrier(self,bridge,operation,releases):
        original=getattr(bridge,operation);entered=threading.Event();release=threading.Event()
        releases.append(release);once=[True]
        def wait_then_call(threshold):
            if once[0]:
                once[0]=False;entered.set()
                if not release.wait(3):raise TimeoutError('Bridge boundary not released')
            return original(threshold)
        setattr(bridge,operation,wait_then_call)
        return entered,release

    def responsive(self,station,*actions):
        errors=[];done=threading.Event()
        def invoke():
            try:
                for action in actions:station.action(action)
            except Exception as error:errors.append(error)
            finally:done.set()
        thread=threading.Thread(target=invoke,daemon=True);thread.start()
        self.assertTrue(done.wait(.75),'UI lock stayed held over the blocked bridge call')
        thread.join(1);self.assertEqual(errors,[])

    def test_frozen_legacy_capture_and_configure_reproduce_mixed_tuple(self):
        for operation,method in (('capture',legacy_capture),('configure',legacy_configure)):
            with self.subTest(operation=operation):
                station,bridge,releases=self.station()
                setattr(bridge,operation,method.__get__(bridge,EthernetBridge))
                entered,release=self.barrier(bridge,operation,releases);errors=[]
                # Explicit caller argument is read before the blocked old method.
                threshold=station.threshold
                def invoke():
                    try:getattr(bridge,operation)(threshold)
                    except Exception as error:errors.append(error)
                worker=threading.Thread(target=invoke,daemon=True);worker.start()
                try:
                    self.assertTrue(entered.wait(2))
                    self.responsive(station,dict(op='recipe',value='synthetic_dark_v137'))
                finally:release.set();worker.join(3)
                self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
                self.assertEqual(bridge.transport.calls,[(operation,(90,True,2,True))])
                PROOFS.append(dict(negative_control=operation,old=OLD,new=NEW,observed=(90,True,2,True)))

    def test_configuration_snapshot_then_new_capture_are_separately_complete(self):
        station,bridge,releases=self.station()
        configured,release_config=self.barrier(bridge,'configure',releases)
        captured,release_capture=self.barrier(bridge,'capture',releases)
        station.action(dict(op='start'));self.assertTrue(configured.wait(2))
        self.responsive(station,dict(op='recipe',value='synthetic_dark_v137'))
        release_config.set();self.assertTrue(captured.wait(2))
        self.responsive(station,dict(op='pause'))
        release_capture.set();self.until(lambda:not station.busy)
        self.assertEqual(bridge.transport.calls,[('configure',OLD),('capture',NEW)])
        self.assertEqual(station.frame['recipe_id'],'synthetic_dark_v137')
        self.assertEqual(bridge.transport.acks,[(7,1)]);self.assertEqual(station.error,'')

    def test_pause_during_frozen_configuration_cancels_capture_by_epoch(self):
        station,bridge,releases=self.station()
        entered,release=self.barrier(bridge,'configure',releases)
        station.action(dict(op='start'));self.assertTrue(entered.wait(2))
        epoch=station.intent_epoch
        self.responsive(station,dict(op='recipe',value='synthetic_dark_v137'),dict(op='pause'))
        self.assertEqual(station.intent_epoch,epoch+1)
        release.set();self.until(lambda:not station.busy)
        self.assertEqual(bridge.transport.calls,[('configure',OLD)])
        self.assertEqual(station.capture_admissions,0);self.assertEqual(bridge.transport.acks,[])
        self.assertEqual(station.cancelled_before_capture,1)

    def test_admitted_manual_capture_stays_old_and_commits_before_ack_after_pause(self):
        station,bridge,releases=self.station()
        entered,release=self.barrier(bridge,'capture',releases)
        ack=bridge.transport.ack;committed=[]
        def checked_ack(boot,event):
            evidence=station.records.all();self.assertEqual(len(evidence),1)
            committed.append((evidence[0]['boot_id'],evidence[0]['event_id']))
            ack(boot,event)
        bridge.transport.ack=checked_ack
        station.action(dict(op='capture'));self.assertTrue(entered.wait(2))
        self.responsive(station,dict(op='recipe',value='synthetic_dark_v137'),dict(op='pause'))
        release.set();self.until(lambda:not station.busy)
        self.assertEqual(bridge.transport.calls,[('capture',OLD)])
        self.assertEqual(station.recipe_id,'synthetic_dark_v137')
        saved=station.records.all();self.assertEqual(len(saved),1)
        self.assertEqual(saved[0]['recipe_id'],'mvtec_hdmi_weak_v124')
        self.assertEqual((saved[0]['applied_threshold'],saved[0]['weak_passes'],saved[0]['low_gate_enabled']),(90,4,False))
        self.assertEqual(committed,bridge.transport.acks);self.assertEqual(committed,[(7,1)])
        self.assertIsNone(station.pending_ack);self.assertIsNone(station.records.confirmations.pending())
        self.assertEqual(station.error,'')

    def test_delayed_captured_configuration_wins_over_both_request_and_ui(self):
        station,bridge,_=self.station();bridge.transport.force_captured=OLD
        station.action(dict(op='recipe',value='synthetic_dark_v137'))
        station.action(dict(op='capture'));self.until(lambda:station.captures==1 and not station.busy)
        self.assertEqual(bridge.transport.calls,[('capture',NEW)])
        self.assertEqual(station.frame['recipe_id'],'mvtec_hdmi_weak_v124')
        self.assertEqual(station.records.all()[0]['recipe_id'],'mvtec_hdmi_weak_v124')
        self.assertEqual(station.error,'')

    def test_transport_wait_does_not_hold_station_lock(self):
        station,bridge,releases=self.station();entered=threading.Event();release=threading.Event();releases.append(release)
        def hook(operation,value):
            entered.set()
            if not release.wait(3):raise TimeoutError('Transport wait not released')
        bridge.transport.hook=hook
        station.action(dict(op='capture'));self.assertTrue(entered.wait(2))
        self.responsive(station,dict(op='recipe',value='synthetic_dark_v137'),dict(op='pause'))
        release.set();self.until(lambda:not station.busy)
        self.assertEqual(bridge.transport.calls,[('capture',OLD)]);self.assertEqual(station.error,'')

    def test_success_and_failure_reset_context_for_later_direct_calls(self):
        for operation in ('configure','capture'):
            for fail in (False,True):
                with self.subTest(operation=operation,fail=fail):
                    bridge=self.bridge();bridge.passes=4
                    request=bridge.bind_request(operation,90)
                    bridge.enhance=False;bridge.passes=2;bridge.low_gate=True;bridge.transport.fail_once=fail
                    if fail:
                        with self.assertRaises(TransientTransportError):request()
                    else:request()
                    getattr(bridge,operation)(37)
                    self.assertEqual(bridge.transport.calls,[(operation,OLD),(operation,(37,False,2,True))])

    def test_existing_override_then_super_keeps_snapshot_for_both_operations(self):
        class Overridden(EthernetBridge):
            def __init__(self):
                super().__init__('127.0.0.1');self.transport=Transport()
                self.entered=threading.Event();self.release=threading.Event()
            def boundary(self):
                self.entered.set()
                if not self.release.wait(3):raise TimeoutError('Override not released')
            def capture(self,threshold):self.boundary();return super().capture(threshold)
            def configure(self,threshold):self.boundary();return super().configure(threshold)
        for operation in ('capture','configure'):
            with self.subTest(operation=operation):
                bridge=Overridden();bridge.passes=4;request=bridge.bind_request(operation,90);errors=[]
                def invoke():
                    try:request()
                    except Exception as error:errors.append(error)
                worker=threading.Thread(target=invoke,daemon=True);worker.start()
                try:
                    self.assertTrue(bridge.entered.wait(2));bridge.passes=2;bridge.low_gate=True
                finally:bridge.release.set();worker.join(3)
                self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
                getattr(bridge,operation)(36)
                self.assertEqual(bridge.transport.calls,[(operation,OLD),(operation,NEW)])

    def test_nested_same_bridge_request_restores_outer_snapshot(self):
        bridge=self.bridge();bridge.passes=4
        outer=bridge.bind_request('configure',90)
        bridge.passes=2;bridge.low_gate=True;inner=bridge.bind_request('configure',36)
        bridge.enhance=False;bridge.low_gate=False
        trace=[]
        def hook(operation,value):
            trace.append(value)
            if len(trace)==1:
                inner()
                bridge.configure(90)  # Still inside the outer request context.
        bridge.transport.hook=hook;outer();bridge.transport.hook=None;bridge.configure(37)
        self.assertEqual(trace,[OLD,NEW,OLD])
        self.assertEqual(bridge.transport.calls[-1],('configure',(37,False,2,False)))

    def test_snapshot_context_does_not_leak_to_other_bridge(self):
        first=self.bridge();second=self.bridge();first.passes=4
        second.enhance=False;second.passes=2;second.low_gate=True
        first.transport.hook=lambda operation,value:second.configure(37)
        first.bind_request('configure',90)()
        self.assertEqual(first.transport.calls,[('configure',OLD)])
        self.assertEqual(second.transport.calls,[('configure',(37,False,2,True))])

    def test_two_threads_on_one_bridge_keep_independent_snapshots(self):
        bridge=self.bridge();barrier=threading.Barrier(3);errors=[]
        original=bridge.configure
        def overridden(threshold):barrier.wait(3);return original(threshold)
        bridge.configure=overridden;bridge.passes=4;old=bridge.bind_request('configure',90)
        bridge.passes=2;bridge.low_gate=True;new=bridge.bind_request('configure',36)
        bridge.enhance=False;bridge.low_gate=False
        def invoke(request):
            try:request()
            except Exception as error:errors.append(error)
        workers=[threading.Thread(target=invoke,args=(request,),daemon=True) for request in (old,new)]
        for worker in workers:worker.start()
        barrier.wait(3)
        for worker in workers:worker.join(3);self.assertFalse(worker.is_alive())
        self.assertEqual(errors,[])
        self.assertEqual(Counter(bridge.transport.calls),Counter([('configure',OLD),('configure',NEW)]))
        bridge.configure=original;bridge.configure(37)
        self.assertEqual(bridge.transport.calls[-1],('configure',(37,False,2,False)))

    def test_legacy_jtag_shaped_bridge_keeps_one_threshold_argument(self):
        raw,descriptor,meta=test_events.packet();frame,image,mask=Bridge.decode_event(raw,descriptor,meta,1)
        class Legacy:
            def __init__(self):self.thresholds=[];self.acks=[]
            def capture(self,threshold):self.thresholds.append(threshold);return frame,image,mask
            def ack(self,frame):self.acks.append((frame['boot_id'],frame['event_id']))
            def close(self):pass
        with tempfile.TemporaryDirectory(prefix='tile_v138_legacy_') as root:
            bridge=Legacy();station=Station(root,bridge)
            try:
                station.action(dict(op='threshold',value=41));station.action(dict(op='capture'))
                self.until(lambda:station.captures==1 and not station.busy)
                self.assertEqual(bridge.thresholds,[41]);self.assertEqual(bridge.acks,[(7,1)])
                self.assertEqual(len(station.records.all()),1);self.assertEqual(station.error,'')
            finally:station.exit=True;station.worker.join(3);station.records.db.close()


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(RecipeSnapshotTests)
    names=[test.id() for test in suite]
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    output=ROOT/'reports/v148';output.mkdir(parents=True,exist_ok=True)
    summary=dict(passed=result.wasSuccessful(),tests=result.testsRun,test_ids=names,negative_controls=PROOFS,
                 failures=len(result.failures),errors=len(result.errors),
                 source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                for name in ('host/workstation.py','host/test_recipe_snapshot.py')},
                 scope='Bounded threads, actual Station/EthernetBridge, stub transport and isolated real archive; no socket or board.')
    (output/'recipe_snapshot_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
