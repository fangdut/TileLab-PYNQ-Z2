"""Bounded V1.38 active-profile switching on the already-running Station.

Local HTTP API only: the Station remains the sole board receiver. This script
does not program a board, launch services, or perform live defect detection.
Run only after the inherited V1.37 BIT/ELF and V1.38 Station/player are ready.
Numerical image/reference comparisons happen after acquisition is paused.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import io
import json
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zlib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'models'), str(ROOT / 'host')]
import numpy as np
from PIL import Image
import recipes
from weak_reference import detect
from regions_reference import regions

BASE = 'http://127.0.0.1:8770'
OUT = ROOT / 'reports/v138/profile_switch_board'
SECONDS = 40
SWITCH_SECONDS = 2
MAX_LIVE_PAIRS = 192
MAX_EVENTS = 32
FIRMWARE = 0x12500
ERROR_FIELDS = ('gaps', 'invalid', 'dropped', 'ack_errors', 'descriptor_crc_errors')
CRC_FIELDS = ('pixel_crc_verified', 'header_crc_verified', 'descriptor_crc_verified')
PROFILES = {
    'A': dict(recipe_id='mvtec_hdmi_weak_v124', threshold=90, enhance=True, passes=4, low_gate=False),
    'B': dict(recipe_id='synthetic_dark_v137', threshold=36, enhance=True, passes=2, low_gate=True),
}


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def state():
    with urllib.request.urlopen(BASE + '/api/state?limit=1', timeout=10) as response:
        value = json.load(response)
    assert value.get('revision') == 'V1.38', 'Refusing a Station other than V1.38'
    return value


def action(op, **fields):
    request = urllib.request.Request(BASE + '/api/action',
        data=json.dumps(dict(op=op, **fields)).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def export_records():
    with urllib.request.urlopen(BASE + '/api/export?format=json', timeout=15) as response:
        return json.load(response)['records']


def image_bytes(frame, mask=False, archived=False):
    query = {'id': frame['id']} if archived else {'frame': str(frame['frame_id']) + '_' + frame['acquired_at']}
    query['mask'] = int(mask)
    with urllib.request.urlopen(BASE + '/api/image?' + urllib.parse.urlencode(query), timeout=10) as response:
        data = response.read()
        if archived:
            digest = hashlib.sha256(data).hexdigest()
            assert response.headers.get('X-Archive-Integrity') == 'sha256-verified'
            assert response.headers.get('X-Archive-SHA256') == digest
            assert frame['mask_sha256' if mask else 'image_sha256'] == digest
    return data


def rgb(data):
    with Image.open(io.BytesIO(data)) as picture:
        return np.asarray(picture.convert('RGB'))


def barcode(pixels):
    return sum(int(pixels[22:38, 1018 + bit * 14:1025 + bit * 14].mean() > 128) << bit for bit in range(16))


def source_tile(code):
    if not 0 <= code < 720:
        return None
    visible = []
    for index in range(4):
        x = ((code * 8 - index * 1440 + 500) % 5760 + 5760) % 5760 - 500
        if x <= 640 < x + 500:
            visible.append(dict(index=index, x=x, full_visible=0 <= x <= 780))
    assert len(visible) <= 1
    return visible[0] if visible else None


def profile_of(frame):
    word = frame['config_word']
    actual = ((word >> 8) & 255, bool(word & (1 << 24)), 4 if word & (1 << 25) else 2, bool(word & (1 << 26)))
    matches = [name for name, p in PROFILES.items()
               if actual == (p['threshold'], p['enhance'], p['passes'], p['low_gate'])]
    assert len(matches) == 1, ('Captured mixed/unrequested tuple', actual, frame['frame_id'])
    return matches[0]


def is_profile(frame, name):
    try:
        return profile_of(frame) == name
    except (KeyError, AssertionError):
        return False


def check_frame(frame, boot, catalog, require_full=False):
    assert frame['boot_id'] == boot and frame['firmware_version'] == FIRMWARE
    assert frame['width'] == 1280 and frame['height'] == 720
    assert all(frame.get(key) is True for key in CRC_FIELDS)
    name = profile_of(frame)
    expected = recipes.evidence(frame, catalog)
    assert expected['recipe_id'] == PROFILES[name]['recipe_id']
    assert all(frame.get(key) == value for key, value in expected.items()), 'Captured attribution differs from descriptor configuration'
    if require_full:
        assert frame['selection'] == 'FPGA_PRODUCT_BEST_FRAME' and frame['selection_full_tile'] is True
        assert frame['product_id'] > 0 and frame['event_reason'] in (1, 2)
    return name


def adopted(value, source, identity):
    player = value['stimulus_status']
    return (player.get('ready') and player.get('identity_confirmed')
            and player.get('observed') == source and player.get('observed_request_id') == identity)


def healthy(value, boot=None):
    stats = value['board_stats']
    assert value['transport'] == 'ETHERNET_TCP' and not value['error'] and not value['recovery']['active']
    assert stats['version'] == FIRMWARE and stats['error_status'] == 0
    if boot is not None:
        assert stats['boot_id'] == boot
    assert value['capture_health']['ready'] and not value['capture_health']['stale']
    assert value['storage']['mode'] == 'archive', 'Automatic archival stopped during bounded test'


def wait_for(predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = state()
        if predicate(value):
            return value
        time.sleep(.05)
    raise TimeoutError('Station condition timeout: ' + json.dumps(value, ensure_ascii=False))


def pause():
    action('pause')
    return wait_for(lambda value: not value['busy'])


def verify_pixels(frame, original, mask_data, boot, catalog, full=False):
    name = check_frame(frame, boot, catalog, full)
    p = PROFILES[name]
    pixels = rgb(original)
    with Image.open(io.BytesIO(mask_data)) as picture:
        mask = np.asarray(picture.convert('L')) > 0
    assert pixels.shape == (720, 1280, 3) and mask.shape == (720, 1280)
    raw = np.empty((720, 1280, 4), np.uint8)
    raw[:, :, :3] = pixels[:, :, ::-1]
    raw[:, :, 3] = mask
    expected, _ = detect(pixels, threshold=p['threshold'], passes=p['passes'])
    grouped = regions(expected)
    code = barcode(pixels)
    tile = source_tile(code)
    check = dict(frame_id=frame['frame_id'], boot_id=frame['boot_id'], event_id=frame['event_id'],
        profile=name, source_barcode=code, source_tile=tile, crc3=True, captured_recipe_attribution=True,
        reconstructed_pixel_crc_matches=zlib.crc32(raw.tobytes()) == frame['pixel_crc32'],
        mask_mismatch=int(np.count_nonzero(mask != expected)), boxes_match=frame['boxes'] == grouped['boxes'],
        areas_match=frame['region_areas'] == grouped['areas'], overflow_match=frame['region_overflow'] == grouped['overflow'],
        candidate_area_match=frame['candidate_pixels'] == int(expected.sum()),
        full_tile=(frame.get('selection_full_tile') is True and tile is not None and tile['full_visible']) if full else None,
        image_sha256=hashlib.sha256(original).hexdigest(), mask_sha256=hashlib.sha256(mask_data).hexdigest())
    check['passed'] = (check['reconstructed_pixel_crc_matches'] and check['mask_mismatch'] == 0
        and all(check[k] for k in ('boxes_match', 'areas_match', 'overflow_match', 'candidate_area_match'))
        and (check['full_tile'] is True if full else True))
    return check


def save_pair(directory, prefix, frame, original, mask_data):
    result = dict(frame=frame, files={}, sha256={})
    for kind, data in (('original', original), ('mask', mask_data)):
        path = directory / (prefix + '_' + kind + '.png')
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        assert sha(path) == digest
        result['files'][kind] = path.name
        result['sha256'][kind] = digest
    return result


def source_provenance():
    names = ['scripts/board_v138_profile_switch.py', 'host/workstation.py', 'host/tcp_transport.py',
             'host/recipes.py', 'host/recipes.json', 'host/ConveyorStimulus.cs',
             'models/weak_reference.py', 'models/valley_reference.py', 'models/regions_reference.py',
             'data/dark_gate/manifest.json']
    names += ['data/dark_gate/tile_' + str(index) + '.png' for index in range(4)]
    return {name: sha(ROOT / name) for name in names}


def programmed_proof():
    path = ROOT / 'reports/programmed_v138.json'
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    assert record['active_application'] == 'hdmi_ethernet' and type(record['boot_id']) is int
    sdk = ROOT / (ROOT.name + '.sdk')
    names = ('system.bit', 'system.xsa', 'hdmi_ethernet/build/hdmi_ethernet.elf')
    actual = {name: sha(sdk / name) for name in names}
    assert all(record['sha256'][name] == value for name, value in actual.items())
    return dict(path=str(path), marker_sha256=sha(path), record=record, artifact_sha256=actual)


def main():
    assert ROOT.name == 'pynq_z2_tile_v1_53'
    OUT.mkdir(parents=True, exist_ok=True)
    run = OUT / ('run_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
    run.mkdir()
    result = dict(passed=False, revision='V1.38', firmware_version=FIRMWARE, started_utc=utc(),
        run_directory=str(run), requested_seconds=SECONDS, switch_interval_seconds=SWITCH_SECONDS,
        profiles=PROFILES, switches=[], live_checks=[], live_evidence=[], events=[], event_images=[], event_checks=[],
        scope='Actual active HTTP recipe switching during synthetic HDMI motion, PL capture and TCP/Station reception; no forced physical reproduction of the original instruction-level race.',
        limitations=['A/B requests can coalesce or wait for a product gap; not every click must become a frame.',
            'Captured configuration determines attribution, including older queue events; current UI selection is not ground truth.',
            'Four repeated synthetic tiles are not independent factory products or a detector accuracy dataset.',
            'A logical product gap is not necessarily a physically empty conveyor, especially for material invisible to the old gate. Atomic tuple transfer does not prove arbitrary live material-switch safety.',
            'Only a bounded selection of live PNG pairs plus all this run automatic-event PNGs is retained.',
            'No human external-monitor/HDMI-output visual confirmation is made.'])
    touched = False
    live = []
    seen = set()
    retained = {'A': 0, 'B': 0}
    try:
        result['source_sha256'] = source_provenance()
        result['startup_programmed_proof'] = programmed_proof()
        write(run / 'provenance.json', {key: result[key] for key in ('source_sha256', 'startup_programmed_proof')})
        catalog = recipes.load(ROOT)
        initial = state()
        assert initial['transport'] == 'ETHERNET_TCP' and initial['board_stats']['version'] == FIRMWARE
        boot = result['startup_programmed_proof']['record']['boot_id']
        assert initial['board_stats']['boot_id'] == boot
        pause()
        touched = True
        empty = action('display', value='station_6')['request_id']
        action('preview_rate', value=2)
        action('freeze_preview', enabled=False)
        action('wire_mode', value='rle')
        action('storage', mode='archive', max_archive_mib=1024)
        action('status')
        action('recipe', value=PROFILES['A']['recipe_id'])
        count = state()['captures']
        action('start')
        warm = wait_for(lambda v: v['captures'] > count and adopted(v, 'station_6', empty)
            and v.get('frame') and is_profile(v['frame'], 'A') and v['board_stats']['depth'] == 0
            and v['board_stats']['current_product_id'] == 0 and not v['pending_operation'])
        healthy(warm, boot)
        old = {event['id'] for event in export_records()}
        before = state()
        result.update(boot_id=boot, before=before['board_stats'])
        begun = time.monotonic()
        source_request = action('display', value='dark_video')['request_id']
        adoption = None
        next_switch = begun + SWITCH_SECONDS
        selected = 'A'
        last_print = begun
        result['evicted_live_pairs'] = 0
        while True:
            value = state()
            healthy(value, boot)
            now = time.monotonic()
            elapsed = now - begun
            if adopted(value, 'dark_video', source_request) and adoption is None:
                adoption = elapsed
            if now >= next_switch and elapsed < SECONDS:
                selected = 'B' if selected == 'A' else 'A'
                started = time.monotonic()
                action('recipe', value=PROFILES[selected]['recipe_id'])
                result['switches'].append(dict(seconds=started - begun, requested_profile=selected,
                    action_ms=(time.monotonic() - started) * 1000, observed_before_frame=(value.get('frame') or {}).get('frame_id'),
                    board_current_product_id=value['board_stats']['current_product_id'], capture_phase=value['capture_control']['phase']))
                # No catch-up burst if HTTP or image fetching delayed this tick.
                next_switch = time.monotonic() + SWITCH_SECONDS
            frame = value.get('frame')
            if adoption is not None and frame:
                identity = (frame['frame_id'], frame['acquired_at'])
                if identity not in seen:
                    name = check_frame(frame, boot, catalog)
                    try:
                        original = image_bytes(frame)
                        mask = image_bytes(frame, True)
                    except urllib.error.HTTPError as error:
                        if error.code != 404:
                            raise
                        result['evicted_live_pairs'] += 1
                    else:
                        seen.add(identity)
                        code = barcode(rgb(original))
                        if 0 <= code < 720:
                            assert len(live) < MAX_LIVE_PAIRS, 'Bounded live evidence limit reached'
                            live.append((dict(frame), original, mask, dict(seconds=elapsed,
                                observed_requested_recipe=value['requested_recipe'], source_barcode=code)))
                            if retained[name] < 2:
                                evidence = save_pair(run, f'live_{name}_{retained[name]}', frame, original, mask)
                                evidence.update(profile=name, source_barcode=code)
                                result['live_evidence'].append(evidence)
                                retained[name] += 1
            if elapsed >= SECONDS and value['board_stats']['current_product_id'] == 0:
                break
            if elapsed > SECONDS + 6:
                raise TimeoutError('No bounded product gap after active switch window')
            if now - last_print >= 10:
                print(json.dumps(dict(seconds=round(elapsed, 2), switches=len(result['switches']),
                    live_pairs=len(live), queue=value['board_stats']['depth'])), flush=True)
                last_print = now
            time.sleep(.07)
        result['video_seconds'] = time.monotonic() - begun
        assert adoption is not None and len(result['switches']) >= 12
        result['player_adopted_after_seconds'] = adoption
        empty = action('display', value='station_6')['request_id']
        wait_for(lambda v: adopted(v, 'station_6', empty) and v['board_stats']['depth'] == 0
            and v['board_stats']['current_product_id'] == 0 and not v['pending_operation'])
        final = pause()
        healthy(final, boot)
        assert not final['pending_operation'] and not final['pending_confirmation']
        after = final['board_stats']
        errors = {key: (after[key] - before['board_stats'][key]) & 0xffffffff for key in ERROR_FIELDS}
        assert not any(errors.values()), errors
        result.update(after=after, final_state=final, error_deltas=errors,
            host_captures=final['captures'] - before['captures'], seconds=time.monotonic() - begun,
            received_bytes_delta=final['transport_totals']['received_bytes'] - before['transport_totals']['received_bytes'],
            products_completed_delta=(after['products_completed'] - before['board_stats']['products_completed']) & 0xffffffff,
            defective_products_delta=(after['defective_products'] - before['board_stats']['defective_products']) & 0xffffffff)
        # Only now run reference vision algorithms on the captured data.
        for frame, original, mask, observation in live:
            check = verify_pixels(frame, original, mask, boot, catalog)
            check.update(observation)
            result['live_checks'].append(check)
            assert check['passed'], check
        assert {check['profile'] for check in result['live_checks']} == {'A', 'B'}, 'Both actually applied profiles must be captured'
        result['observed_profile_counts'] = {name: sum(c['profile'] == name for c in result['live_checks']) for name in PROFILES}
        events = [event for event in export_records() if event['id'] not in old]
        result['events'] = events
        assert 0 < len(events) <= MAX_EVENTS, 'Expected bounded automatic product evidence'
        assert len(events) == result['defective_products_delta']
        assert len({(event['boot_id'], event['product_id']) for event in events}) == len(events)
        for index, event in enumerate(events):
            original = image_bytes(event, archived=True)
            mask = image_bytes(event, True, True)
            evidence = save_pair(run, f'event_{index:03d}', event, original, mask)
            evidence['record_id'] = event['id']
            result['event_images'].append(evidence)
            check = verify_pixels(event, original, mask, boot, catalog, full=True)
            check['record_id'] = event['id']
            result['event_checks'].append(check)
            assert check['passed'] and 0 <= check['source_barcode'] < 720, check
        result['saved_events'] = len(events)
        result['sources_unchanged'] = source_provenance() == result['source_sha256']
        result['programmed_artifacts_unchanged'] = programmed_proof() == result['startup_programmed_proof']
        assert result['sources_unchanged'] and result['programmed_artifacts_unchanged']
        result['passed'] = True
    except Exception:
        result.update(error=traceback.format_exc(), collected_live_pairs=len(live))
        raise
    finally:
        cleanup = []
        if touched:
            for operation in (pause, lambda: action('storage', mode='preview', max_archive_mib=1024),
                              lambda: action('display', value='station_6')):
                try:
                    operation()
                except Exception as error:
                    cleanup.append(str(error))
        result['cleanup_errors'] = cleanup
        if cleanup:
            result['passed'] = False
        result['finished_utc'] = utc()
        write(run / 'summary.json', result)
        write(OUT / 'summary.json', result)
    print(json.dumps({key: result[key] for key in ('passed', 'boot_id', 'video_seconds', 'host_captures',
        'saved_events', 'observed_profile_counts', 'error_deltas', 'cleanup_errors')}), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
