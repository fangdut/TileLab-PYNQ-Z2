"""Bounded diagnostics checks; select --board or --loopback explicitly.

--board uses only an already-running V1.45 Station HTTP API at port 8770.
It does not program hardware/start services and leaves reception paused, on
an empty source, in preview-only mode. It creates one manual archive record.
--loopback uses temporary SQLite/PNG files and random local HTTP/TCP ports;
it never contacts port 8770 or the physical board.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import io
import json
import select
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zlib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = 0x12a00
ERRORS = ('gaps', 'invalid', 'dropped', 'ack_errors', 'descriptor_crc_errors')
CRCS = ('pixel_crc_verified', 'header_crc_verified', 'descriptor_crc_verified')
BUSY_STATUS = ('Wait for current transfer or diagnostics before requesting status',
               'Finish or resume the pending capture/confirmation before diagnostics')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def source_hashes(loopback=False):
    names = ['scripts/board_v145_helpers.py', 'host/workstation.py', 'host/tcp_transport.py',
             'host/recipes.py', 'host/recipes.json', 'host/preview_policy.py', 'host/event_identity.py',
             'host/capture_health.py', 'host/dma_recovery.py', 'host/word_rle.py', 'host/packed_pixels.py']
    if loopback:
        names.append('scripts/test_preview_tcp_load.py')
    else:
        names += ['host/ConveyorStimulus.cs', 'data/dark_gate/manifest.json']
        names += [f'data/dark_gate/tile_{i}.png' for i in range(4)]
    return {name: sha(ROOT / name) for name in names}


class Client:
    def __init__(self, url):
        self.url = url

    def get(self, path):
        with urllib.request.urlopen(self.url + path, timeout=10) as response:
            return json.load(response)

    def state(self):
        value = self.get('/api/state?limit=1')
        assert value['revision'] == 'V1.45'
        return value

    def action(self, op, **values):
        request = urllib.request.Request(self.url + '/api/action', data=json.dumps(dict(op=op, **values)).encode(),
                                         headers={'Content-Type': 'application/json'})
        begun = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                data, code = json.load(response), response.status
        except urllib.error.HTTPError as error:
            data, code = json.loads(error.read()), error.code
        return dict(op=op, status=code, milliseconds=(time.monotonic() - begun) * 1000, response=data)

    def ok(self, op, **values):
        result = self.action(op, **values)
        assert result['status'] == 200, result
        return result

    def records(self):
        return self.get('/api/export?format=json')['records']

    def image(self, frame, mask=False, archived=False):
        query = {'id': frame['id']} if archived else {'frame': str(frame['frame_id']) + '_' + frame['acquired_at']}
        query['mask'] = int(mask)
        with urllib.request.urlopen(self.url + '/api/image?' + urllib.parse.urlencode(query), timeout=10) as response:
            data = response.read()
            if archived:
                digest = hashlib.sha256(data).hexdigest()
                assert response.headers.get('X-Archive-Integrity') == 'sha256-verified'
                assert response.headers.get('X-Archive-SHA256') == digest
                assert frame['mask_sha256' if mask else 'image_sha256'] == digest
            return data


def wait_for(client, predicate, seconds=15):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = client.state()
        if predicate(value):
            return value
        time.sleep(.03)
    raise TimeoutError('Bounded state condition was not met')


def paused(client):
    result = client.ok('pause')
    value = wait_for(client, lambda state: not state['busy'])
    assert not value['enabled'] and not value['manual_waiting']
    return result, value


def async_action(client, op):
    result = {}
    entered = threading.Event()
    def invoke():
        result['started'] = time.monotonic()
        entered.set()
        try:
            result['action'] = client.action(op)
        except Exception:
            result['error'] = traceback.format_exc()
        finally:
            result['finished'] = time.monotonic()
    thread = threading.Thread(target=invoke, daemon=True)
    thread.start()
    assert entered.wait(2)
    return thread, result


def status_outcome(result, boot, firmware):
    if result['status'] == 200:
        value = result['response']
        assert value['boot_id'] == boot and value['version'] == firmware and value['error_status'] == 0
        return 'accepted'
    assert result['status'] == 400 and result['response'].get('error') in BUSY_STATUS, result
    return 'busy_rejected'


def checked_pixels(frame, original, mask_data, boot, firmware):
    import numpy as np
    from PIL import Image
    assert frame['boot_id'] == boot and frame['firmware_version'] == firmware
    assert frame['width'] == 1280 and frame['height'] == 720 and all(frame.get(key) is True for key in CRCS)
    with Image.open(io.BytesIO(original)) as picture:
        rgb = np.asarray(picture.convert('RGB'))
    with Image.open(io.BytesIO(mask_data)) as picture:
        mask = np.asarray(picture.convert('L'))
    assert rgb.shape == (720, 1280, 3) and mask.shape == (720, 1280)
    assert np.all((mask == 0) | (mask == 255))
    raw = np.empty((720, 1280, 4), np.uint8)
    raw[:, :, :3] = rgb[:, :, ::-1]
    raw[:, :, 3] = mask > 0
    result = dict(frame_id=frame['frame_id'], event_id=frame['event_id'], boot_id=boot, firmware_version=firmware,
        complete_720p_frame=True, crc3=True, reconstructed_pixel_crc_matches=zlib.crc32(raw.tobytes()) == frame['pixel_crc32'],
        candidate_count_matches=int((mask > 0).sum()) == frame['candidate_pixels'],
        image_sha256=hashlib.sha256(original).hexdigest(), mask_sha256=hashlib.sha256(mask_data).hexdigest())
    result['passed'] = result['reconstructed_pixel_crc_matches'] and result['candidate_count_matches']
    assert result['passed'], result
    return result


def save_evidence(directory, stem, frame, original, mask, check):
    item = dict(frame=frame, check=check, files={}, sha256={})
    for name, data in (('original', original), ('mask', mask)):
        path = directory / (stem + '_' + name + '.png')
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        assert sha(path) == digest
        item['files'][name] = path.name
        item['sha256'][name] = digest
    return item


def programmed_proof():
    path = ROOT / 'reports/programmed_v145.json'
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    assert record['active_application'] == 'hdmi_ethernet' and type(record['boot_id']) is int
    sdk = ROOT / (ROOT.name + '.sdk')
    actual = {name: sha(sdk / name) for name in ('system.bit', 'system.xsa', 'hdmi_ethernet/build/hdmi_ethernet.elf')}
    assert all(record['sha256'][name] == digest for name, digest in actual.items())
    return dict(path=str(path), marker_sha256=sha(path), record=record, artifact_sha256=actual)


def adopted(value, source, request):
    p = value['stimulus_status']
    return p.get('ready') and p.get('identity_confirmed') and p.get('observed') == source and p.get('observed_request_id') == request


def healthy(value, boot):
    assert value['transport'] == 'ETHERNET_TCP' and not value['error'] and not value['recovery']['active']
    assert value['board_stats']['boot_id'] == boot and value['board_stats']['version'] == FIRMWARE
    assert value['board_stats']['error_status'] == 0 and value['storage']['mode'] == 'preview'


def board(result, run):
    client = Client('http://127.0.0.1:8770')
    result['source_sha256'] = source_hashes()
    result['startup_programmed_proof'] = programmed_proof()
    write(run / 'provenance.json', {key: result[key] for key in ('source_sha256', 'startup_programmed_proof')})
    boot = result['startup_programmed_proof']['record']['boot_id']
    result.update(boot_id=boot, firmware_version=FIRMWARE, windows=[], live_evidence=[], manual_evidence=[], pause_measurements=[])
    touched = False
    try:
        initial = client.state()
        assert initial['board_stats']['boot_id'] == boot and initial['board_stats']['version'] == FIRMWARE
        touched = True
        paused(client)
        request = client.ok('display', value='station_6')['response']['request_id']
        client.ok('preview_rate', value=2)
        client.ok('freeze_preview', enabled=False)
        client.ok('storage', mode='preview', max_archive_mib=1024)
        client.ok('wire_mode', value='rle')
        status_outcome(client.ok('status'), boot, FIRMWARE)
        client.ok('recipe', value='mvtec_hdmi_weak_v124')
        old = {record['id'] for record in client.records()}
        count = client.state()['captures']
        client.ok('start')
        warm = wait_for(client, lambda value: value['captures'] > count and adopted(value, 'station_6', request)
            and value['board_stats']['depth'] == 0 and value['board_stats']['current_product_id'] == 0
            and not value['pending_operation'])
        healthy(warm, boot)
        result['before'] = warm['board_stats']
        request = client.ok('display', value='dark_video')['response']['request_id']
        wait_for(client, lambda value: adopted(value, 'dark_video', request))
        for index in range(3):
            client.ok('start')
            begun = time.monotonic()
            count = client.state()['captures']
            window = dict(index=index, status_requests=[], live_pair_retained=False)
            result['windows'].append(window)
            next_status = begun
            while time.monotonic() - begun < 4:
                value = client.state()
                healthy(value, boot)
                now = time.monotonic()
                if now >= next_status and not value['busy']:
                    response = client.action('status')
                    outcome = status_outcome(response, boot, FIRMWARE)
                    window['status_requests'].append(dict(seconds=now - begun, outcome=outcome,
                        milliseconds=response['milliseconds'], error=response['response'].get('error')))
                    next_status = time.monotonic() + .25
                frame = value.get('frame')
                if not window['live_pair_retained'] and frame and value['captures'] > count:
                    try:
                        original, mask = client.image(frame), client.image(frame, True)
                    except urllib.error.HTTPError as error:
                        if error.code != 404:
                            raise
                    else:
                        check = checked_pixels(frame, original, mask, boot, FIRMWARE)
                        result['live_evidence'].append(save_evidence(run, f'live_{index}', frame, original, mask, check))
                        window['live_pair_retained'] = True
                time.sleep(.07)
            # Physical status is normally very fast: record actual overlap,
            # never pretend this phase deterministically delays a board reply.
            thread, diagnostic = async_action(client, 'status')
            pause_started = time.monotonic()
            response, final = paused(client)
            pause_finished = time.monotonic()
            thread.join(16)
            assert not thread.is_alive() and 'error' not in diagnostic, diagnostic
            outcome = status_outcome(diagnostic['action'], boot, FIRMWARE)
            measure = dict(window=index, pause_http_ms=response['milliseconds'],
                pause_and_inflight_completion_ms=(pause_finished - pause_started) * 1000,
                concurrent_status_outcome=outcome,
                status_thread_overlap=diagnostic['started'] <= pause_started < diagnostic['finished'])
            result['pause_measurements'].append(measure)
            assert response['milliseconds'] < 1500, 'Physical HTTP Pause exceeded the bounded engineering check'
            stopped_count = final['captures']
            time.sleep(.25)
            stopped = client.state()
            assert stopped['captures'] == stopped_count and not stopped['enabled'] and not stopped['busy']
            assert not stopped['pending_operation'] and not stopped['pending_confirmation']
            window.update(seconds=time.monotonic() - begun, captures=stopped_count - count, paused_stays_stopped=True)
            assert window['captures'] >= 2 and window['live_pair_retained']
        status_rows = [row for window in result['windows'] for row in window['status_requests']]
        result['status_accepted'] = sum(row['outcome'] == 'accepted' for row in status_rows)
        result['status_busy_rejected'] = sum(row['outcome'] == 'busy_rejected' for row in status_rows)
        assert result['status_accepted'] >= 3
        # Drain using explicit empty source before the single manual archive.
        request = client.ok('display', value='station_6')['response']['request_id']
        count = client.state()['captures']
        client.ok('start')
        wait_for(client, lambda value: value['captures'] > count and adopted(value, 'station_6', request)
            and value['board_stats']['depth'] == 0 and value['board_stats']['current_product_id'] == 0
            and not value['pending_operation'])
        paused(client)
        assert {record['id'] for record in client.records()} == old, 'Preview test unexpectedly added an archive'
        count = client.state()['captures']
        client.ok('capture')
        during_manual = client.action('status')
        result['status_during_manual'] = dict(outcome=status_outcome(during_manual, boot, FIRMWARE),
                                             milliseconds=during_manual['milliseconds'])
        final = wait_for(client, lambda value: value['captures'] == count + 1 and not value['busy']
                         and not value['pending_operation'] and not value['pending_confirmation'])
        healthy(final, boot)
        records = [record for record in client.records() if record['id'] not in old]
        assert len(records) == 1 and records[0]['reason'] == 'manual'
        frame = records[0]
        original, mask = client.image(frame, archived=True), client.image(frame, True, True)
        check = checked_pixels(frame, original, mask, boot, FIRMWARE)
        result['manual_evidence'].append(save_evidence(run, 'manual', frame, original, mask, check))
        result['manual_record_id'] = frame['id']
        result['after'] = final['board_stats']
        result['error_deltas'] = {name: (result['after'][name] - result['before'][name]) & 0xffffffff for name in ERRORS}
        assert not any(result['error_deltas'].values())
        assert result['after']['depth'] == 0
        result['final_control'] = {key: final[key] for key in ('enabled', 'busy', 'captures', 'manual_waiting', 'pending_operation', 'pending_confirmation', 'capture_control')}
        result['manual_saved_and_confirmation_completed'] = True
        result['sources_unchanged'] = source_hashes() == result['source_sha256']
        result['programmed_artifacts_unchanged'] = programmed_proof() == result['startup_programmed_proof']
        assert result['sources_unchanged'] and result['programmed_artifacts_unchanged']
        result['passed'] = True
    finally:
        errors = []
        if touched:
            for operation in (lambda: paused(client), lambda: client.ok('storage', mode='preview', max_archive_mib=1024),
                              lambda: client.ok('display', value='station_6')):
                try:
                    operation()
                except Exception as error:
                    errors.append(str(error))
        result['cleanup_errors'] = errors
        if errors:
            result['passed'] = False


def loopback(result, run):
    # Imports and services only in the explicitly selected local fixture mode.
    sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'host')]
    from http.server import ThreadingHTTPServer
    from workstation import EthernetBridge, Station, handler
    from test_preview_tcp_load import FixtureServer, BOOT, VERSION
    result['source_sha256'] = source_hashes(True)
    write(run / 'provenance.json', {'source_sha256': result['source_sha256']})

    class DelayedServer(FixtureServer):
        def __init__(self, directory):
            self.entered = threading.Event()
            self.release = threading.Event()
            self.delay_once = True
            self.delayed_seconds = None
            super().__init__(directory)

        def reply(self, op, a, b):
            if op == 3 and self.delay_once:
                self.delay_once = False
                begun = time.monotonic()
                self.entered.set()
                if not self.release.wait(4):
                    raise TimeoutError('Loopback delayed status was not released')
                self.delayed_seconds = time.monotonic() - begun
            return super().reply(op, a, b)

    with tempfile.TemporaryDirectory(prefix='tile_v140_diagnostics_') as temporary:
        directory = Path(temporary)
        (directory / 'host').mkdir()
        (directory / 'host/recipes.json').write_bytes((ROOT / 'host/recipes.json').read_bytes())
        sender = DelayedServer(directory)
        bridge = EthernetBridge('127.0.0.1')
        bridge.transport.port = sender.port
        bridge.transport.compression = False
        bridge.transport.read_idle_timeout = 3
        station = Station(directory, bridge)
        sender.station = station
        http = ThreadingHTTPServer(('127.0.0.1', 0), handler(station))
        http_thread = threading.Thread(target=http.serve_forever, daemon=True)
        http_thread.start()
        client = Client('http://127.0.0.1:' + str(http.server_port))
        diagnostic_thread = None
        try:
            diagnostic_thread, diagnostic = async_action(client, 'status')
            assert sender.entered.wait(2)
            held = client.state()
            assert held['busy'] and held['capture_control']['phase'] == 'DIAGNOSTIC'
            pause_reply = client.ok('pause')
            assert pause_reply['milliseconds'] < 500 and diagnostic_thread.is_alive() and not sender.release.is_set()
            start_reply = client.ok('start')
            assert start_reply['milliseconds'] < 500
            rejected = {op: client.action(op) for op in ('capture', 'status', 'disconnect', 'resume_pending')}
            assert all(response['status'] == 400 for response in rejected.values()), rejected
            value = client.state()
            assert value['enabled'] and value['busy'] and value['captures'] == 0
            time.sleep(.15)
            # The fixture consumed the diagnostic's 16-byte request before
            # blocking. Any further readability means an illegal competing
            # request (or close) reached this same real socket while reserved.
            concurrent_bytes = bool(select.select([sender.connection], [], [], 0)[0])
            assert not concurrent_bytes and bridge.transport.requests_sent == 1
            client.ok('pause')
            sender.release.set()
            diagnostic_thread.join(4)
            assert not diagnostic_thread.is_alive() and 'error' not in diagnostic, diagnostic
            assert status_outcome(diagnostic['action'], BOOT, VERSION) == 'accepted'
            status_timing = dict(bridge.transport.last_timing)
            assert status_timing['header_crc_verified'] is True and status_timing['uncompressed_bytes'] == 0
            final = wait_for(client, lambda v: not v['busy'])
            assert not final['enabled'] and final['captures'] == 0 and final['capture_control']['phase'] == 'IDLE'
            # Reservation release must also allow a later normal full-size
            # capture, durable manual save and ACK on that same connection.
            with sender.lock:
                sender.manual_next = True
            client.ok('capture')
            final = wait_for(client, lambda v: v['captures'] == 1 and not v['busy']
                             and not v['pending_operation'] and not v['pending_confirmation'])
            rows = client.records()
            assert len(rows) == 1
            original, mask = client.image(rows[0], archived=True), client.image(rows[0], True, True)
            check = checked_pixels(rows[0], original, mask, BOOT, VERSION)
            transport = sender.snapshot()
            assert not transport['failures'] and len(transport['acks']) == 1
            assert transport['acks'][0]['saved_before_ack'] and transport['queue_depth'] == 0
            assert bridge.transport.reconnects == 0 and not final['error']
            result.update(passed=True, diagnostic_delay_seconds=sender.delayed_seconds,
                pause_http_ms=pause_reply['milliseconds'], start_http_ms=start_reply['milliseconds'],
                pause_completed_before_status_release=True, start_intent_queued_without_capture=True,
                reserved_phase_observed='DIAGNOSTIC', rejected_during_diagnostic={k: v['response']['error'] for k, v in rejected.items()},
                requests_sent_before_release=1, competing_socket_bytes_before_release=False,
                release_kept_latest_pause=True, manual_frame_check=check, manual_saved_before_ack=True,
                pending_confirmation=False, status_header_crc_verified=status_timing['header_crc_verified'],
                protocol_fixture_version=VERSION, ports=dict(http=http.server_port, tcp=sender.port),
                transport=dict(requests=len(transport['requests']), acks=len(transport['acks']),
                               bytes_received=bridge.transport.total_received_bytes, reconnects=bridge.transport.reconnects),
                sources_unchanged=source_hashes(True) == result['source_sha256'])
            assert result['sources_unchanged']
        finally:
            sender.release.set()
            if diagnostic_thread:
                diagnostic_thread.join(4)
            station.action(dict(op='pause'))
            station.exit = True
            station.worker.join(4)
            bridge.close()
            http.shutdown()
            http.server_close()
            http_thread.join(3)
            sender.close()
            station.records.db.close()
            assert not station.worker.is_alive() and not http_thread.is_alive()
    result['temporary_business_files_removed'] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--board', action='store_true')
    mode.add_argument('--loopback', action='store_true')
    args = parser.parse_args()
    assert ROOT.name == 'pynq_z2_tile_v1_53'
    output = ROOT / 'reports/v145' / ('diagnostics_board' if args.board else 'diagnostics_loopback')
    run = output / ('run_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
    run.mkdir(parents=True)
    result = dict(passed=False, revision='V1.45', mode='board' if args.board else 'loopback',
        started_utc=datetime.now(timezone.utc).isoformat(), run_directory=str(run),
        scope='Bounded physical Station diagnostics integration' if args.board else 'Actual local HTTP/TCP with delayed fixture status and temporary business files; no physical board',
        limitations=['Physical status replies may finish before Pause starts; observed thread overlap does not prove a blocked physical TCP wait.',
            'The loopback mode deterministically withholds a response; its timing is not board throughput or a real-link latency measurement.',
            'CRC and complete image transport do not measure detector accuracy; the detector and firmware are inherited.',
            'Loopback descriptor-CRC verification is a sender protocol declaration; real header/pixel CRC validation uses production EventTCP.',
            'Pause response is separate from waiting for an already admitted transfer to finish.',
            'No new external-monitor visual confirmation or physical HDMI hotplug test.'])
    try:
        (board if args.board else loopback)(result, run)
    except Exception:
        result.update(passed=False, error=traceback.format_exc())
        raise
    finally:
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write(run / 'summary.json', result)
        write(output / 'summary.json', result)
    print(json.dumps(dict(passed=result['passed'], mode=result['mode'], summary=str(output / 'summary.json'))), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
