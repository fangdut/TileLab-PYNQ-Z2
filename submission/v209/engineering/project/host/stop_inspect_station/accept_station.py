"""Exercise the running local UI API with physical FPGA inference.

Expected labels are evaluated only after receiving each FPGA result. This is
the exposed demonstration set, not a new independent accuracy benchmark.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time
import urllib.request
import urllib.error


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='http://127.0.0.1:8793')
    p.add_argument('--expected', type=Path, required=True)
    p.add_argument('--store', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    expected = json.loads(a.expected.read_text())
    records = []
    guards = []

    def request(path, body=None):
        req = urllib.request.Request(a.url+path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    def action(op, **values):
        state = request('/api/state')
        return request('/api/action', dict(op=op, session=state['session'], revision=state['revision'], **values))

    def wait():
        deadline = time.monotonic()+30
        while time.monotonic() < deadline:
            state = request('/api/state')
            if state['phase'] not in ['INSPECTING', 'CONFIRMING']:
                return state
            time.sleep(.05)
        raise TimeoutError('Station action did not finish')

    def reject(op, **values):
        try:
            action(op, **values)
        except urllib.error.HTTPError as error:
            assert error.code == 409
            guards.append(dict(op=op, rejected=True, error=json.load(error)['error']))
            return
        raise AssertionError('Unsafe action unexpectedly accepted: '+op)

    initial = request('/api/state')
    assert initial['phase'] == 'READY', 'Use a fresh station session for acceptance'
    (a.out/'plan.json').write_text(json.dumps(dict(scope='PHYSICAL_STOP_INSPECT_WORKFLOW_EXPOSED_DEMO',
        session=initial['session'],selected_before_detection=[r['id'] for r in initial['samples']],
        benchmark_is_blind=False,physical_actuator_connected=False), indent=2))
    for sample in initial['samples']:
        state = action('load', sample_id=sample['id'])
        ident = state['cycle']['id']
        assert state['phase'] == 'STOPPED' and state['cycle']['result'] is None
        reject('release', operator_confirmed=True, result_id='old-result')
        state = action('inspect', input_held_confirmed=True)
        state = wait()
        assert state['phase'] in ['GOOD_HOLD', 'DEFECT_HOLD'], state
        result = state['cycle']['result']
        # Only now consult external ground truth for evaluation.
        truth = expected[sample['id']]
        assert result['pl_image_alarm'] == truth['expected_alarm'], sample['id']
        assert result['cpu_detection'] is False and result['gpu_detection'] is False
        assert not state['logical_release_requested'] and state['stop_requested']
        reject('release', operator_confirmed=True, result_id='wrong-result-id')
        if result['pl_image_alarm']:
            reject('release', operator_confirmed=True, result_id=result['id'])
        op = 'segregate' if result['pl_image_alarm'] else 'release'
        start = time.perf_counter()
        action(op, operator_confirmed=True, result_id=result['id'])
        final = wait()
        assert final['phase'] == ('SEGREGATED' if result['pl_image_alarm'] else 'RELEASED')
        cycle_file = a.store/'cycles'/ident/'cycle.json'
        records.append(dict(sample_id=sample['id'],label=truth['label'],cycle_id=ident,
            fpga_alarm=result['pl_image_alarm'],boot_identity=result['boot_identity'],
            frame_sequence=result['pl_frame_sequence'],engine_seconds=result['pl_engine_seconds'],
            transfer_and_detection_seconds=result['wall_seconds'],disposition=op,
            confirm_roundtrip_seconds=time.perf_counter()-start,
            cycle_sha256=hashlib.sha256(cycle_file.read_bytes()).hexdigest(),
            result_sha256=result['result_sha256']))
        (a.out/'results.json').write_text(json.dumps(records,indent=2))
        print('PHYSICAL_CYCLE_PASS',len(records),truth['label'],result['pl_image_alarm'],flush=True)
    (a.out/'guard_rejections.json').write_text(json.dumps(guards,ensure_ascii=False,indent=2),encoding='utf8')
    summary = dict(scope='PHYSICAL_FPGA_STOP_INSPECT_WORKFLOW_EXPOSED_DEMO',cycles=len(records),
        correct=len(records),normal_images=sum(r['label']=='good' for r in records),
        normal_false_alarms=0,defects_detected=sum(r['fpga_alarm'] for r in records),
        confirmed_good_releases=sum(r['disposition']=='release' for r in records),
        confirmed_defect_segregations=sum(r['disposition']=='segregate' for r in records),
        unsafe_actions_rejected=len(guards),cpu_detection=False,gpu_detection=False,
        pc_responsibilities=['original photo decode/transport','operator workflow','result display','audit logging'],
        physical_actuator_connected=False,physical_actuation_verified=False,
        benchmark_is_blind=False,speed_target_required_for_this_milestone=False,
        mean_engine_seconds=sum(r['engine_seconds'] for r in records)/len(records),
        mean_transfer_and_detection_seconds=sum(r['transfer_and_detection_seconds'] for r in records)/len(records))
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary),flush=True)


if __name__ == '__main__':
    main()
