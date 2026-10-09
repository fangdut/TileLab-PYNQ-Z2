"""Bounded real-board Station/API comparison, executed only by main().

Requires the V1.35 station and HDMI player already running. Does not program
hardware or start services. The offline NumPy model checks archived FPGA output;
it never supplies live decisions. Uses only local helpers, never old board tools.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import io
import json
import sys
import time
import traceback
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'models'))
import numpy as np
from PIL import Image
from weak_reference import detect
from regions_reference import regions

BASE = 'http://127.0.0.1:8770'
OUT = ROOT / 'reports/v135/board_preview_rates'
RATES = (0, 5, 2)
SECONDS = 60
ERROR_FIELDS = ('gaps', 'dropped', 'invalid', 'ack_errors', 'descriptor_crc_errors')
CRC_FIELDS = ('pixel_crc_verified', 'header_crc_verified', 'descriptor_crc_verified')


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def state():
    with urllib.request.urlopen(BASE + '/api/state?limit=1', timeout=10) as response:
        value = json.load(response)
    if value.get('revision') != 'V1.35':
        raise RuntimeError('Refusing a station revision other than V1.35')
    return value


def action(op, **fields):
    request = urllib.request.Request(BASE + '/api/action',
        data=json.dumps(dict(op=op, **fields)).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def records():
    with urllib.request.urlopen(BASE + '/api/export?format=json', timeout=15) as response:
        return json.load(response)['records']


def image(record, mask=False):
    query = urllib.parse.urlencode(dict(id=record['id'], mask=int(mask)))
    with urllib.request.urlopen(BASE + '/api/image?' + query, timeout=10) as response:
        data = response.read()
        assert response.headers.get('X-Archive-Integrity') == 'sha256-verified'
        digest = hashlib.sha256(data).hexdigest()
        assert response.headers.get('X-Archive-SHA256') == digest
    assert record['mask_sha256' if mask else 'image_sha256'] == digest
    return data


def healthy(value):
    assert not value['error'], value['error']
    assert not value['recovery']['active'], value['recovery']
    health = value['capture_health']
    assert health['ready'] and not health['stale'], health
    assert value['board_stats']['version'] == 0x12000
    assert value['board_stats']['error_status'] == 0


def wait_for(predicate, timeout=12, require_health=False):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = state()
        if require_health:
            healthy(value)
        if predicate(value):
            return value
        time.sleep(.05)
    raise TimeoutError('Timed out waiting for station: ' + json.dumps(value, ensure_ascii=False))


def pause():
    action('pause')
    return wait_for(lambda value: not value['busy'])


def adopted(value, source, request_id):
    stimulus = value['stimulus_status']
    return (stimulus.get('ready') and stimulus.get('identity_confirmed')
            and stimulus.get('observed') == source
            and stimulus.get('observed_request_id') == request_id)


def barcode(data):
    rgb = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'))
    return sum(int(rgb[22:38, 1018+b*14:1025+b*14].mean() > 128) << b for b in range(16))


def delta(after, before, field):
    return (after[field] - before[field]) & 0xffffffff


def verify_events(events, timeline):
    checks, mapping = [], []
    for event in sorted(events, key=lambda item: item['frame_id']):
        original = image(event)
        mask_data = image(event, True)
        actual = np.asarray(Image.open(io.BytesIO(mask_data))) > 0
        expected, _ = detect(Image.open(io.BytesIO(original)).convert('RGB'), threshold=90, passes=4)
        expected_regions = regions(expected)
        code = barcode(original)
        assert 0 <= code < len(timeline), ('Invalid moving-source barcode', code)
        central = [tile for tile in timeline[code]['visible'] if tile['x'] <= 640 < tile['x']+500]
        assert len(central) == 1, ('Ambiguous source product', event['id'], code)
        tile = central[0]
        check = dict(record_id=event['id'],
            mask_mismatch=int(np.count_nonzero(actual != expected)),
            boxes_match=event['boxes'] == expected_regions['boxes'],
            areas_match=event['region_areas'] == expected_regions['areas'],
            overflow_match=event['region_overflow'] == expected_regions['overflow'],
            candidate_area_match=event['candidate_pixels'] == int(expected.sum()),
            full_tile=bool(event['selection_full_tile']) and 0 <= tile['x'] <= 780,
            crc3=all(event.get(field) is True for field in CRC_FIELDS),
            captured_quad_threshold_90=(event.get('applied_threshold') == 90 and event.get('weak_passes') == 4),
            source_label_is_crack=tile['label'] == 'crack')
        check['passed'] = check['mask_mismatch'] == 0 and all(
            check[key] for key in ('boxes_match','areas_match','overflow_match','candidate_area_match',
                                  'full_tile','crc3','captured_quad_threshold_90','source_label_is_crack'))
        checks.append(check)
        mapping.append(dict(record_id=event['id'], boot_id=event['boot_id'], product_id=event['product_id'],
            event_id=event['event_id'], frame_id=event['frame_id'], source_frame_barcode=code,
            source_photo_id=tile['id'], source_label=tile['label'], tile_left_x=tile['x'],
            center_error_px=abs(tile['x']+250-640), selection_full_tile=event['selection_full_tile']))
    return checks, mapping


def run_rate(rate, run, timeline):
    result = dict(passed=False, preview_rate_fps=rate, started_utc=now(), requested_video_seconds=SECONDS)
    samples = []
    try:
        pause()
        empty_request = action('display', value='station_6')['request_id']
        action('recipe', value='mvtec_hdmi_weak_v124')
        action('wire_mode', value='rle')
        action('preview_rate', value=rate)
        # Preserve any pre-existing retained event during warmup. Its record is
        # excluded from this run only after the queue is proven empty.
        action('storage', mode='archive', max_archive_mib=1024)
        count = state()['captures']
        action('start')
        warm = wait_for(lambda value: value['captures'] > count
            and adopted(value, 'station_6', empty_request)
            and (value.get('frame') or {}).get('weak_passes') == 4
            and value.get('applied_threshold') == 90
            and value['board_stats']['depth'] == 0
            and value['board_stats']['current_product_id'] == 0
            and not value['pending_operation'], timeout=15)
        healthy(warm)
        prior = {record['id'] for record in records()}
        before_state = state()
        before = before_state['board_stats']
        started = time.monotonic()
        real_request = action('display', value='real_video')['request_id']
        ready_at = None
        last_progress = started
        while True:
            value = state()
            healthy(value)
            stats = value['board_stats']
            assert stats['boot_id'] == before['boot_id'], 'Board restarted during run'
            elapsed = time.monotonic() - started
            if adopted(value, 'real_video', real_request) and ready_at is None:
                ready_at = elapsed
            samples.append(dict(seconds=elapsed, captures=value['captures'], queue_depth=stats['depth'],
                products_completed=stats['products_completed'], defective_products=stats['defective_products'],
                current_product_id=stats['current_product_id'], received_bytes=value['transport_totals']['received_bytes'],
                capture_health=value['capture_health']['state'], pending=value['pending_operation'],
                source_frame=value['stimulus_status'].get('source_frame')))
            if elapsed >= SECONDS and stats['current_product_id'] == 0:
                assert ready_at is not None, 'Player never confirmed requested moving source'
                break
            if elapsed > SECONDS + 6:
                raise TimeoutError('No product gap at end of bounded video interval')
            if time.monotonic() - last_progress >= 15:
                print(json.dumps(dict(rate=rate, seconds=round(elapsed, 2), queue=stats['depth'],
                                      captures=value['captures']-before_state['captures'])), flush=True)
                last_progress = time.monotonic()
            time.sleep(.08)
        video_seconds = time.monotonic() - started
        empty_request = action('display', value='station_6')['request_id']
        # The last completed product belongs to this run even if its event is
        # still being transmitted when the video source changes to an empty belt.
        wait_for(lambda value: adopted(value, 'station_6', empty_request)
            and value['board_stats']['current_product_id'] == 0
            and value['board_stats']['depth'] == 0 and not value['pending_operation'],
            timeout=12, require_health=True)
        final = pause()
        healthy(final)
        measured_seconds = time.monotonic() - started
        after = final['board_stats']
        assert after['boot_id'] == before['boot_id']
        events = [record for record in records() if record['id'] not in prior]
        checks, mapping = verify_events(events, timeline)
        error_deltas = {field: delta(after, before, field) for field in ERROR_FIELDS}
        product_ids = [(record['boot_id'], record.get('product_id')) for record in events]
        assert len(events) >= 8, 'Too few archived defects in the 60-second sequence'
        assert len(set(product_ids)) == len(events), 'Duplicate physical-product evidence'
        assert all(record.get('selection') == 'FPGA_PRODUCT_BEST_FRAME' for record in events)
        assert all(check['passed'] for check in checks), checks
        assert all(value == 0 for value in error_deltas.values()), error_deltas
        assert delta(after, before, 'defective_products') == len(events), 'Board alarms and saved product count differ'
        assert not final['pending_operation'] and not final['pending_confirmation']
        assert not final['confirmation_journal']['error'] and not final['synchronization_warning']
        assert after['depth'] == 0 and final['storage']['scan_complete']
        result.update(passed=True, firmware_version=after['version'], boot_id=after['boot_id'],
            seconds=measured_seconds, video_seconds=video_seconds, player_adopted_after_seconds=ready_at,
            received_bytes_delta=final['transport_totals']['received_bytes']-before_state['transport_totals']['received_bytes'],
            requests_delta=final['transport_totals']['requests']-before_state['transport_totals']['requests'],
            host_captures=final['captures']-before_state['captures'], queue_peak_observed=max(sample['queue_depth'] for sample in samples),
            saved_events=len(events), products_completed_delta=delta(after,before,'products_completed'),
            defective_products_delta=delta(after,before,'defective_products'), captured_delta=delta(after,before,'captured'),
            error_deltas=error_deltas, before=before, after=after, checks=checks, product_mapping=mapping,
            events=events, samples=samples, final_state=final,
            coverage_scope='Every board-declared defective product in this measured interval is archived; repeated source photos are not independent factory samples.')
    except Exception:
        result.update(error=traceback.format_exc(), samples=samples)
        try:
            result['failure_state'] = state()
        except Exception as error:
            result['failure_state_error'] = str(error)
        raise
    finally:
        result['finished_utc'] = now()
        write_json(run / f'rate_{rate}.json', result)
    return result


def main():
    # Verify the already-running service before any control mutation.
    initial = state()
    assert initial['transport'] == 'ETHERNET_TCP'
    assert initial['preview_rate_supported']
    run = OUT / ('run_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    run.mkdir(parents=True)
    manifest = json.loads((ROOT/'data/real_tiles/video_manifest.json').read_text(encoding='utf-8'))
    summary = dict(passed=False, revision='V1.35', started_utc=now(), run_directory=str(run),
        scope='Actual HDMI/PL/TCP/Station archive comparison at 0/5/2 preview fps; offline reference used only after capture.',
        program_proof='reports/programmed_v135.json', ready_proof='reports/v135/boot_readiness.json',
        source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
            ('host/workstation.py','host/preview_policy.py','host/archive_inventory.py','host/tcp_transport.py',
             'scripts/board_v135_preview_rates.py','models/weak_reference.py','models/regions_reference.py')},
        limitations=['Repeated real tile photos move synthetically; this is not a blind industrial accuracy test.',
                     'Byte totals include status/configure/ACK traffic and final drain; observed queue peak is sampled.',
                     'Preview rates limit ordinary host sampling, not FPGA pixel processing or queued defect delivery.'], cases=[])
    try:
        for rate in RATES:
            item = run_rate(rate, run, manifest['timeline'])
            summary['cases'].append(item)
            write_json(run/'progress.json', summary)
            print(json.dumps({key:item[key] for key in ('passed','preview_rate_fps','seconds','received_bytes_delta',
                                                       'host_captures','saved_events','queue_peak_observed')}), flush=True)
        assert len({item['boot_id'] for item in summary['cases']}) == 1
        assert all(item['firmware_version'] == 0x12000 for item in summary['cases'])
        summary.update(passed=True, boot_id=summary['cases'][0]['boot_id'], firmware_version=0x12000)
    except Exception:
        summary['error'] = traceback.format_exc()
        raise
    finally:
        cleanup_errors = []
        for fn in (pause, lambda:action('storage',mode='preview',max_archive_mib=1024),
                   lambda:action('display',value='station_6')):
            try:
                fn()
            except Exception as error:
                cleanup_errors.append(str(error))
        summary['cleanup_errors'] = cleanup_errors
        if cleanup_errors:
            summary['passed'] = False
        summary['finished_utc'] = now()
        write_json(run/'summary.json', summary)
        write_json(OUT/'summary.json', summary)
    assert summary['passed'], summary


if __name__ == '__main__':
    main()
