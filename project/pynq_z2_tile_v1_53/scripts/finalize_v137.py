"""Verify V1.37 evidence, then seal a concise delivery (no build/board access).

--check-only reads and hashes files only; it does not create directories, open
the business database, import Station, or write a report. Run only after the
fresh hardware/firmware audits and both physical-board tests have finished.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os

R = Path(__file__).resolve().parents[1]
O = R / 'reports/v137'
W = R / (R.name + '.sdk')
VERSION = 'V1.37'
FIRMWARE = 0x12500
MAGIC = 0x54465337
STATUS = 'BOARD_VALIDATED_OPTIONAL_LOW_LUMINANCE_PRODUCT_GATE'
ERRORS = ('gaps', 'invalid', 'dropped', 'ack_errors', 'descriptor_crc_errors')
CRCS = ('pixel_crc_verified', 'header_crc_verified', 'descriptor_crc_verified')
BOUND = {}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def checked(path, expected):
    path = Path(path).resolve()
    actual = sha(path)
    require(actual == expected, 'Changed executed input/output: ' + str(path))
    BOUND[str(path)] = actual
    return actual


def load(path):
    path = Path(path)
    data = path.read_bytes()
    BOUND[str(path.resolve())] = hashlib.sha256(data).hexdigest()
    return json.loads(data.decode('utf-8-sig'))


def hashes(root, values):
    require(bool(values), 'Empty hash evidence: ' + str(root))
    for name, digest in values.items():
        checked(Path(root) / name, digest)


def inside(parent, child):
    path = (Path(parent) / child).resolve()
    require(path.is_relative_to(Path(parent).resolve()), 'Evidence path escapes its directory: ' + str(path))
    return path


def passed(value, name):
    require(value.get('passed') is True, name + ' did not pass')


def board_stats(value, boot):
    require(value['boot_id'] == boot and value['version'] == FIRMWARE,
            'Board boot/firmware mismatch')
    require(value['error_status'] == 0, 'Board reports an active error')


def no_errors(value):
    require(set(value) >= set(ERRORS) and all(value[k] == 0 for k in ERRORS),
            'Missing or nonzero physical error deltas')


def captured(frame, boot, high, passes, low, full=False):
    require(frame['boot_id'] == boot and frame['firmware_version'] == FIRMWARE,
            'Captured frame boot/firmware mismatch')
    require(all(frame.get(k) is True for k in CRCS), 'Missing one of three frame CRC checks')
    require(frame['width'] == 1280 and frame['height'] == 720, 'Unexpected captured dimensions')
    word = frame['config_word']
    require(((word >> 8) & 255) == high and bool(word & (1 << 24))
            and bool(word & (1 << 25)) == (passes == 4)
            and bool(word & (1 << 26)) == low, 'Captured profile differs from tested recipe')
    if full:
        require(frame.get('selection_full_tile') is True, 'Best-frame evidence is not a complete tile')


def verify_host():
    host = load(O / 'host_validation.json')
    passed(host, 'Host validation')
    require(host['version'] == VERSION and host['unit_tests']['passed'] is True
            and host['unit_tests']['count'] >= 343
            and not host['unit_tests']['failures'] and not host['unit_tests']['errors'], 'Host unit regression incomplete')
    hashes(R, host['source_sha256'])
    for name, minimum in (('review_ui', 19), ('preview_ui', 11), ('inventory_ui', 10)):
        ui = host[name]
        passed(ui, name)
        require(ui['tests'] >= minimum and len(ui['cases']) == ui['tests']
                and all(case['passed'] is True for case in ui['cases']), 'Incomplete ' + name)
        if 'html_sha256' in ui:
            checked(R / 'host/workstation.html', ui['html_sha256'])
    checked(R / 'host/review_session.js', host['review_ui']['session_source_sha256'])
    require(host['archive_implementation_ast_unchanged'] is True, 'Archive implementation changed')
    native = host['native_stimulus']
    require(native['passed'] is True and native['actual_renderer_compiled'] is True
            and native['player_script_syntax'] is True, 'Native player validation incomplete')
    tcp = host['tcp_load']
    passed(tcp, 'Loopback TCP')
    hashes(R, tcp['source_sha256'])
    require({case['preview_rate_fps'] for case in tcp['cases']} == {0, 2, 5}, 'Missing loopback preview rate')
    require(all(case['passed'] is True and case['all_headers_and_pixels_crc_validated'] is True
                and case['all_saved_events_committed_before_ack'] is True for case in tcp['cases']), 'Loopback integrity/ACK failure')
    require(load(O / 'preview_tcp_load/summary.json') == tcp, 'Embedded TCP proof differs from output')
    process = host['storage_process']
    passed(process, 'Storage process tests')
    require(all(case['passed'] is True for case in process['cases']), 'Storage process case failed')
    mapping = {'baseline/workstation.py': R.parent / 'pynq_z2_tile_v1_34/host/workstation.py',
               'current/workstation.py': R / 'host/workstation.py',
               'current/archive_inventory.py': R / 'host/archive_inventory.py',
               'test_script': R / 'scripts/test_storage_rollback_process.py'}
    require(set(process['source_sha256']) == set(mapping), 'Unrecognized storage execution inputs')
    for name, path in mapping.items():
        checked(path, process['source_sha256'][name])
    require(load(O / 'storage_rollback_process/summary.json') == process, 'Embedded process proof differs from output')
    return host


def verify_simulation(baseline):
    # The scoped gate/ABI change must not silently replace the detector, tracker,
    # HDMI output pipeline, IP sources, or constraints inherited from V1.36.
    for folder in ('rtl', 'constraints', 'ip_repo'):
        current = {p.relative_to(R).as_posix(): p for p in files_under(R / folder)}
        previous = {p.relative_to(baseline).as_posix(): p for p in files_under(baseline / folder)}
        require(set(current) == set(previous), 'Production PL file inventory changed: ' + folder)
        for name, path in current.items():
            if name != 'rtl/frame_capture_sg.v':
                checked(path, sha(previous[name]))
    original = load(O / 'product_gate_experiment/summary.json')
    passed(original, 'Negative gate baseline')
    require(original['production_rtl_modified'] is False
            and len(original['cases']) == 2
            and all(case['expected_failure_reproduced'] is True for case in original['cases']), 'Original failure reproduction missing')
    for name, digest in original['source_sha256'].items():
        checked((baseline if name.startswith('rtl/') else R) / name, digest)
    require(original['cases'][0]['product_starts'] == 0 and original['cases'][1]['product_starts'] == 2,
            'Unexpected negative baseline result')
    gate = load(O / 'product_gate_validation/summary.json')
    passed(gate, 'Gate module validation')
    hashes(R, gate['source_sha256'])
    require(gate['frames_checked'] == gate['descriptor_crc_checks'] == 57
            and int(gate['descriptor_magic'], 16) == MAGIC
            and gate['default_gate_threshold'] == 320 and gate['low_gate_threshold'] == 160,
            'Gate frame/CRC/ABI coverage mismatch')
    expected = {'default_dark_unchanged': (0, 0), 'default_dip_unchanged': (2, 2),
                'low_dark_one_product': (1, 1), 'low_dip_one_product': (1, 1),
                'inclusive_luma_boundaries': (2, 2), 'frame_config_lock': (1, 1)}
    require({case['name'] for case in gate['cases']} == set(expected), 'Missing gate scenario')
    for case in gate['cases']:
        require(case['passed'] is True and (case['product_starts'], case['product_ends']) == expected[case['name']],
                'Gate scenario mismatch: ' + case['name'])
    capture = load(O / 'capture_regression/summary.json')
    passed(capture, 'Capture regression')
    hashes(R, capture['source_sha256'])
    checked(R / 'rtl/frame_capture_sg.v', capture['production_rtl_sha256'])
    require(capture['hardware_executed'] is False
            and {case['name'] for case in capture['cases']} == {'crc', 'equivalence', 'sg', 'random_equivalence'},
            'Capture simulation coverage mismatch')
    for case in capture['cases']:
        passed(case, 'Capture ' + case['name'])
        # Inspect only named outputs, never collect a generated simulation project or WDB.
        path = inside(O, case['simulation_log'])
        BOUND[str(path)] = sha(path)
        if case['independent_crc_report']:
            crc = load(inside(O, case['independent_crc_report']))
            passed(crc, 'Independent packet CRC')
            require(len(crc['checks']) == 7 and sum(c['invalid'] for c in crc['checks']) == 1,
                    'Missing six valid packets plus one deliberately incomplete packet')
            checked(inside(O, crc['packets_path']), crc['packets_sha256'])
    return gate, capture


def verify_hardware_and_firmware(plan):
    hardware = load(O / 'hardware_audit.json')
    passed(hardware, 'Fresh hardware audit')
    require(hardware['revision'] == VERSION and hardware['new_hardware'] is True, 'Inherited hardware audit')
    require(min(hardware[k] for k in ('wns_ns', 'whs_ns', 'wpws_ns')) >= 0
            and hardware['bus_skew_constraints_met'] == 8
            and all(hardware[k] == 0 for k in ('cdc_unsafe_endpoints', 'cdc_unknown_endpoints', 'cdc_missing_async_reg_endpoints')),
            'Hardware timing or CDC failure')
    hashes(R, hardware['source_sha256'])
    hashes(R / 'reports', hardware['reports_sha256'])
    hashes(W, hardware['artifacts_sha256'])
    hashes(O, hardware['implemented_clock_evidence_sha256'])
    checked(R / (R.name + '.runs') / 'impl_1/system_wrapper_routed.dcp', hardware['routed_checkpoint_sha256'])
    checked(O / 'product_gate_validation/summary.json', hardware['product_gate_validation_sha256'])
    checked(O / 'reset_netlist.txt', hardware['reset_netlist_sha256'])
    require(len(hardware['reset_recovery_removal_reports']) == 4, 'Missing reset timing evidence')
    for name, result in hardware['reset_recovery_removal_reports'].items():
        checked(O / name, result['sha256'])
        require(result['paths'] == 3 and result['minimum_slack_ns'] >= 0, 'Reset timing failure')
    require(load(O / 'max_delay_audit.json') == hardware['max_delay_audit'], 'Max-delay output differs from audit')
    require(hardware['max_delay_audit']['passed'] is True and len(hardware['max_delay_audit']['groups']) == 8,
            'Missing cross-clock maximum-delay constraints')
    historical = hardware['baseline_resource_evidence']
    require(hardware['baseline_revision'] == 'V1.32', 'Resource baseline mislabelled')
    checked(R.parent / historical['report'], historical['sha256'])
    native = load(O / 'firmware_native_summary.json')
    passed(native, 'Native firmware regression')
    hashes(W / 'ethernet_sources', native['source_sha256'])
    hashes(O, native['proof_sha256'])
    require(len(native['proof_sha256']) == 8, 'Expected eight native firmware proof groups')
    for name in native['proof_sha256']:
        proof = load(O / name)
        if name == 'native_sg/result.json':
            require(proof.get('result') == 'PASS', 'Native SG regression failed')
            checked(W / 'ethernet_sources/main.c', proof['main_sha256'])
        else:
            passed(proof, 'Native firmware ' + name)
    gate = load(O / 'product_gate_native/summary.json')
    checked(R / 'scripts/test_product_gate_native.py', gate['script_sha256'])
    firmware = load(O / 'firmware_audit.json')
    passed(firmware, 'Fresh firmware audit')
    require(firmware['revision'] == VERSION and firmware['firmware_version'] == FIRMWARE
            and firmware['descriptor_magic'] == MAGIC and firmware['new_bit_xsa_elf'] is True
            and firmware['authored_imported_sources_match'] is True, 'Firmware version/build mismatch')
    require(set(firmware['source_changes']) == {'main.c', 'network.c', 'event_queue.h'}, 'Unexpected firmware change scope')
    hashes(W / 'ethernet_sources', firmware['source_sha256'])
    hashes(W / 'hdmi_ethernet/src', firmware['source_sha256'])
    hashes(W, firmware['hardware_sha256'])
    hashes(R, firmware['build_config_sha256'])
    checked(R / 'scripts/audit_v137_firmware.py', firmware['audit_script_sha256'])
    checked(O / 'firmware_native_summary.json', firmware['native_proof_sha256'])
    checked(W / 'hdmi_ethernet/build/hdmi_ethernet.elf', firmware['elf_sha256'])
    require(firmware['hardware_sha256'] == hardware['artifacts_sha256']
            and list(firmware['xsa_embedded_bit_sha256'].values()) == [hardware['artifacts_sha256']['system.bit']],
            'Hardware/firmware/XSA BIT disagreement')
    require(firmware['irq_fp_saved'] is True and firmware['irq_stack_bytes'] == 4096
            and firmware['integer_memcpy_preserved'] is True and firmware['hard_float_abi'] is True
            and firmware['bsp_fpu_macro'] is True and firmware['optimization'] == '-O2'
            and firmware['fno_builtin_memcpy'] is True
            and firmware['elf_version_immediates'] and firmware['elf_magic_immediates'], 'Linked firmware safeguards missing')
    require(firmware['backup_sha256'] == plan['backup_sha256']
            and firmware['baseline_manifest_sha256'] == plan['baseline_manifest_sha256'], 'Firmware baseline provenance mismatch')
    artifacts = dict(hardware['artifacts_sha256'])
    artifacts['hdmi_ethernet/build/hdmi_ethernet.elf'] = firmware['elf_sha256']
    for name in ('system.bit', 'system.xsa', 'hdmi_ethernet/build/hdmi_ethernet.elf'):
        require(artifacts[name] != plan['inherited_hardware_sha256'][name], 'Fresh artifact required: ' + name)
    return hardware, firmware, native, artifacts


def verify_real(boot, program):
    real = load(O / 'real_board/summary.json')
    passed(real, 'Physical historical-photo regression')
    require(real['firmware_version'] == FIRMWARE and real['high'] == 90 and real['passes'] == 4
            and real['low_gate'] is False and real['product_gate_sum'] == 320
            and real['samples'] == real['pixel_exact'] == len(real['items']) == 50,
            'Default-profile 50-image regression incomplete')
    require(real['sources_unchanged'] is True and real['programmed_artifacts_unchanged'] is True
            and not real.get('cleanup_error'), 'Physical test source/artifact changed or cleanup failed')
    hashes(R, real['source_sha256'])
    provenance = load(O / 'real_board/provenance.json')
    require(provenance['source_sha256'] == real['source_sha256']
            and provenance['startup_programmed_proof'] == real['startup_programmed_proof'], 'Physical startup provenance mismatch')
    startup = real['startup_programmed_proof']
    require(Path(startup['path']).resolve() == (R / 'reports/programmed_v137.json').resolve()
            and startup['record'] == program, 'Physical test used a different programming record')
    checked(R / 'reports/programmed_v137.json', startup['marker_sha256'])
    hashes(R, startup['artifact_sha256'])
    for name in ('initial', 'before', 'after'):
        board_stats(real[name], boot)
    no_errors(real['error_deltas'])
    require(real['counts']['crack'] == {'total': 17, 'alarms': 17}
            and real['counts']['good'] == {'total': 33, 'alarms': 0}, 'Historical alarm regression changed')
    samples = {item['id']: item for item in load(R.parent / 'pynq_z2_tile_v1_5/data/real_tiles/manifest.json')['samples']}
    require(len({row['id'] for row in real['items']}) == 50, 'Repeated real-photo identifier')
    for row in real['items']:
        passed(row, 'Physical real-photo row')
        captured(row['frame'], boot, 90, 4, False)
        require(row['profile_match'] is True and row['candidate_pixels_match'] is True
                and row['boxes_match'] is True and row['mismatch'] == row['baseline_rgb_mismatch'] == 0,
                'Physical RGB/mask/region regression mismatch')
        require(row['barcode'] == 0x6000 + row['index'] and row['request_id'], 'Missing captured source identity')
        stem = f"real_{row['index']:03d}"
        checked(O / 'real_board' / (stem + '_original.png'), row['image_sha256'])
        checked(O / 'real_board' / (stem + '_mask.png'), row['mask_sha256'])
        checked(R.parent / 'pynq_z2_tile_v1_24/reports/v124/real_board' / (stem + '_original.png'), row['baseline_rgb_sha256'])
        mask = samples[row['id']].get('mask')
        if mask:
            checked(R.parent / 'pynq_z2_tile_v1_5/data/real_tiles' / mask, row['ground_truth_sha256'])
        else:
            require(row['ground_truth_sha256'] is None, 'Unexpected ground truth for good image')
    return real


def verify_dark(boot):
    dark = load(O / 'dark_gate_board/summary.json')
    passed(dark, 'Physical controlled dark-tile comparison')
    require(dark['revision'] == VERSION and dark['boot_id'] == boot and dark['firmware_version'] == FIRMWARE,
            'Dark-board boot/firmware mismatch')
    hashes(R, dark['source_sha256'])
    run = inside(O / 'dark_gate_board', dark['run_directory'])
    require(load(run / 'summary.json') == dark, 'Dark-board run/summary mismatch')
    require(len(dark['cases']) == 2 and {c['name'] for c in dark['cases']} == {'legacy_gate_320', 'low_gate_160'},
            'Missing old/new gate physical comparison')
    for case in dark['cases']:
        passed(case, case['name'])
        directory = run / case['name']
        require(load(directory / 'summary.json') == case and not case['cleanup_errors'], 'Dark-board case output/cleanup mismatch')
        low = case['name'] == 'low_gate_160'
        require(case['low_gate'] is low and case['boot_id'] == boot and case['firmware_version'] == FIRMWARE,
                'Dark-board case profile mismatch')
        board_stats(case['before'], boot)
        board_stats(case['after'], boot)
        no_errors(case['error_deltas'])
        require(case['after']['depth'] == 0 and not case['final_state']['pending_operation']
                and not case['final_state']['pending_confirmation'], 'Physical event queue/confirmation not drained')
        events, checks, pictures = case['events'], case['checks'], case['event_images']
        require(len(events) == len(checks) == len(pictures) == case['saved_events'] == case['defective_products_delta'],
                'Dark-board event/evidence count mismatch')
        require(all(case['observed_source_class_counts'].get(kind, 0) >= 3
                    for kind in ('dark_good', 'dark_crack', 'bright_good', 'bright_crack')),
                'Insufficient bounded source passes')
        require(case['alarm_class_counts'].get('bright_crack', 0) >= 3
                and (case['alarm_class_counts'].get('dark_crack', 0) >= 3 if low else case['alarm_class_counts'].get('dark_crack', 0) == 0),
                'Dark presence repair not demonstrated')
        require(len({(event['boot_id'], event['product_id']) for event in events}) == len(events), 'Duplicate product archive')
        ids = {event['id'] for event in events}
        require(len(ids) == len(events) and {c['record_id'] for c in checks} == {p['record_id'] for p in pictures} == ids,
                'Dark event/image/check identity mismatch')
        by_id = {event['id']: event for event in events}
        for event in events:
            captured(event, boot, 36, 2, low, full=True)
            require(event['selection'] == 'FPGA_PRODUCT_BEST_FRAME' and event['product_id'] > 0,
                    'Automatic archive was not a PL-selected product frame')
        for check in checks:
            require(check['passed'] is True and check['mask_mismatch'] == 0
                    and all(check[k] is True for k in ('crc3', 'reconstructed_pixel_crc_matches', 'profile_matches',
                        'boxes_match', 'areas_match', 'overflow_match', 'candidate_area_match', 'full_tile')),
                    'Dark best-frame exactness/CRC/full-tile failure')
        for picture in pictures:
            event = by_id[picture['record_id']]
            require(all(picture[k] == event[k] for k in ('boot_id', 'product_id', 'event_id')), 'Archived PNG identity mismatch')
            for kind, field in (('original', 'image_sha256'), ('mask', 'mask_sha256')):
                require(picture['sha256'][kind] == event[field], 'Archived PNG hash differs from event')
                checked(inside(directory, picture['files'][kind]), picture['sha256'][kind])
        mapping = case['product_mapping']
        source_passes = [row['source_pass'] for row in mapping]
        require(len(source_passes) == len(set(source_passes)) == len(events)
                and set(source_passes) == set(case['expected_alarm_source_passes'])
                and {row['record_id'] for row in mapping} == ids
                and case['products_completed_delta'] == len(case['expected_tracked_source_passes']),
                'Source-pass/product accounting mismatch')
        live = case['live_dark_proof']
        require(load(directory / 'dark_live_proof.json') == live, 'Live dark proof output mismatch')
        captured(live['frame'], boot, 36, 2, low)
        check = live['check']
        require(check['passed'] is True and check['mask_mismatch'] == 0
                and all(check[k] is True for k in ('crc3', 'reconstructed_pixel_crc_matches', 'profile_matches',
                    'boxes_match', 'areas_match', 'overflow_match', 'candidate_area_match')), 'Live dark image proof failed')
        patch = live['measured_surface']
        require(patch['within_low_but_below_legacy_gate'] is True and patch['pixel_count'] == 3600
                and 160 <= patch['weighted_sum_min'] <= patch['weighted_sum_max'] < 320,
                'Actual captured dark surface did not lie between gate thresholds')
        frame = live['frame']
        require(frame['candidate_pixels'] > 0 and frame['alarm'] is True
                and (frame['product_id'] > 0 if low else frame['product_id'] == 0),
                'Old-dark missing-product versus new-dark present-product was not reproduced')
        for kind in ('original', 'mask'):
            checked(inside(directory, live[kind]), live['sha256'][kind])
    fixture = load(R / 'data/dark_gate/manifest.json')
    require(fixture['kind'] == 'SYNTHETIC_CONTROLLED_FIXTURE_NOT_REAL_TILE' and len(fixture['tiles']) == 4,
            'Controlled fixture missing or mislabelled')
    for tile in fixture['tiles']:
        checked(R / 'data/dark_gate' / f"tile_{tile['index']}.png", tile['sha256'])
    return dark


def verify_limits():
    rejected = load(O / 'weak_candidate/result.json')
    require(rejected['completed'] is True and rejected['status'] == 'REGRESSION_REJECTED'
            and rejected['candidate_eligible_for_isolated_rtl'] is False
            and rejected['production_changed'] is False and rejected['board_tested'] is False
            and rejected['normal_images_checked'] == 230 and rejected['regression_images'] == 50
            and rejected['checks']['precision_floor_met'] is False, 'Rejected weak candidate provenance missing')
    checked(O / 'weak_candidate/declaration.json', rejected['declaration_sha256'])
    declaration = load(O / 'weak_candidate/declaration.json')
    for name, item in declaration['input_files'].items():
        checked(Path(name), item['sha256'])
    race = load(O / 'next_iteration_analysis/mixed_profile_baseline.json')
    require(race['negative_baseline_reproduced'] is True and race['production_modified'] is False
            and race['hardware_used'] is False and race['network_forbidden'] is True,
            'Known recipe-switch limitation not accurately recorded')
    hashes(R, race['source_sha256'])
    require({c['operation'] for c in race['cases']} == {'capture', 'configure'}
            and all(c['mixed_tuple_reproduced'] is True and c['archive_rows'] == c['ack_calls'] == 0 for c in race['cases']),
            'Mixed-profile negative host proof incomplete')
    return rejected, declaration, race


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def files_under(folder):
    for parent, directories, files in os.walk(folder, followlinks=False):
        directories[:] = [name for name in directories if name not in ('__pycache__', 'runtime', 'review_records')
                           and not (Path(parent) / name).is_symlink() and not (Path(parent) / name).is_junction()]
        for name in files:
            path = Path(parent) / name
            if not path.is_symlink():
                yield path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    require(R.name == 'pynq_z2_tile_v1_53' and not R.is_symlink() and not R.is_junction(), 'Wrong project root')
    plan = load(R / 'ITERATION_PLAN.json')
    require(plan['version'] == VERSION, 'Wrong iteration plan')
    baseline = Path(plan['baseline'])
    require(baseline.name == 'pynq_z2_tile_v1_36', 'Expected sealed V1.36 baseline')
    checked(baseline / 'DELIVERY_MANIFEST.json', plan['baseline_manifest_sha256'])
    old = load(baseline / 'DELIVERY_MANIFEST.json')
    for group in ('source_sha256', 'proof_sha256'):
        hashes(baseline, old[group])
    checked(Path(plan['backup']), plan['backup_sha256'])
    host = verify_host()
    gate, capture = verify_simulation(baseline)
    hardware, firmware, native, artifacts = verify_hardware_and_firmware(plan)
    program = load(R / 'reports/programmed_v137.json')
    ready = load(O / 'boot_readiness.json')
    passed(ready, 'Boot readiness')
    require(program['active_application'] == 'hdmi_ethernet' and type(program['boot_id']) is int,
            'No Ethernet programming proof')
    boot = program['boot_id']
    board_stats(ready['state'], boot)
    hashes(W, program['sha256'])
    for name in ('system.bit', 'system.xsa', 'hdmi_ethernet/build/hdmi_ethernet.elf'):
        require(program['sha256'][name] == artifacts[name], 'Programmed/audited artifact mismatch')
    real = verify_real(boot, program)
    dark = verify_dark(boot)
    rejected, declaration, race = verify_limits()
    index = R.parent / 'TileLab_进度与回退.md'
    old_index = index.read_text(encoding='utf-8')
    for marker in ('更新：', '## 当前产品', '## 尚在进行', '## 回退和空间'):
        require(marker in old_index, 'Progress index structure changed: ' + marker)
    if args.check_only:
        print(json.dumps(dict(version=VERSION, passed=True, writes=False, boot_id=boot,
                              verified_files=len(BOUND), unit_tests=host['unit_tests']['count'])))
        return

    limits = [
        'Low product-presence gate is optional and material-specific: captured R+2G+B >=160; default >=320 is unchanged. A sufficiently dark belt and suitable lighting remain necessary.',
        'Product gap remains two frames and best-frame ranking remains full tile/center/area. This release does not solve every tracking, partial occlusion, or centering failure.',
        'The 50 photographs are historical development regression, not blind factory accuracy. Four synthetic moving fixtures repeat; their source passes are not independent factory products.',
        'This release automatically validates HDMI input/PL/capture/TCP. No new human external-monitor or analog HDMI-output visual confirmation was obtained.',
        'Known P2: changing recipes during active acquisition can forward a mixed parameter tuple. Pause, show explicit empty source and drain before switching; atomic recipe snapshot is planned for V1.38 and is not fixed here.',
        'Native C and module simulations are separate evidence from ARM/board execution. Passing CRC and routed CDC checks does not establish detection accuracy, complete hotplug recovery or absence of physical metastability.',
        'Finite queues and PNG/SQLite power-loss boundaries remain. No claim of zero tool warnings: one simulation startup Common 17-354 is retained with its completed-run review.',
    ]
    report_path = lambda path: dict(path=Path(path).relative_to(R).as_posix(), sha256=sha(path))
    summary = dict(version=VERSION, status=STATUS, passed=True, completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Optional PL presence gate, matched ARM/host ABI, and bounded physical-board regressions; crack detector unchanged',
        host_validation=report_path(O / 'host_validation.json'), unit_tests=host['unit_tests'],
        frontend_tests=sum(host[name]['tests'] for name in ('review_ui', 'preview_ui', 'inventory_ui')),
        module_validation=dict(**report_path(O / 'product_gate_validation/summary.json'), frames=gate['frames_checked'], cases=gate['cases']),
        capture_regression=report_path(O / 'capture_regression/summary.json'),
        hardware_audit=dict(**report_path(O / 'hardware_audit.json'), wns_ns=hardware['wns_ns'], whs_ns=hardware['whs_ns'], resources=hardware['resources'], resource_baseline='V1.32'),
        firmware_audit=report_path(O / 'firmware_audit.json'), firmware_native=dict(**report_path(O / 'firmware_native_summary.json'), counts=native['counts']),
        programming=report_path(R / 'reports/programmed_v137.json'), boot_readiness=report_path(O / 'boot_readiness.json'),
        board_test=dict(performed=True, boot_id=boot, firmware_version=FIRMWARE,
            real_photos=dict(**report_path(O / 'real_board/summary.json'), samples=real['samples'], counts=real['counts'], pixel_exact=real['pixel_exact'], pixel_precision=real['pixel_precision'], pixel_recall=real['pixel_recall'], error_deltas=real['error_deltas']),
            controlled_dark=dict(**report_path(O / 'dark_gate_board/summary.json'), cases=[{k:case[k] for k in ('name', 'video_seconds', 'saved_events', 'products_completed_delta', 'defective_products_delta', 'alarm_class_counts', 'error_deltas')} for case in dark['cases']])),
        rejected_weak_candidate=dict(**report_path(O / 'weak_candidate/result.json'), status=rejected['status'], candidate_precision=rejected['summary']['candidate']['pixel_precision'], precision_floor=declaration['gates']['min_crack_pixel_precision'], deployed=False),
        next_iteration=dict(**report_path(O / 'next_iteration_analysis/mixed_profile_baseline.json'), priority='P2', planned='V1.38 atomic recipe snapshot', fixed_in_this_release=False), limits=limits)
    by_name = {case['name']: case for case in dark['cases']}
    before, after = by_name['legacy_gate_320'], by_name['low_gate_160']
    readme = f'''# TileLab V1.37

状态：{STATUS}。

本版修复一个明确的产品跟踪边界：暗色瓷砖可能已产生裂纹候选，却因表面亮度不足而没有产品编号和自动留图。FPGA 增加可选低亮度门槛，表面判定由 `R+2G+B≥320` 改为 `≥160`；配置逐帧锁存。默认门槛、裂纹检测算法、两帧离场判定和最佳帧排序保持原样。ARM/Vitis 与电脑端同步新增配置、版本及描述格式，提供显式低亮度配方；检测仍在 FPGA，电脑参考算法仅用于离线核验。

验证：{host['unit_tests']['count']} 项主机、{summary['frontend_tests']} 项前端、8 组编译 C 回归通过；生产 RTL 的 57 帧门限/帧内配置/描述 CRC 检查及 4 组采集回归通过。新 BIT、XSA、ELF 已构建并在同一次板卡启动中验收；路由 WNS={hardware['wns_ns']:.3f} ns、WHS={hardware['whs_ns']:.3f} ns，8 组跨域最大延迟及总线偏斜检查通过，报告的不安全 CDC 端点为 0。不是零警告声明。

实板默认配方历史 50 图：{real['pixel_exact']}/50 图与参考掩码和历史 RGB 一致；17 张裂纹图报警、33 张正常图无报警。合成连续暗/亮瓷砖对照分别运行 {before['video_seconds']:.2f}/{after['video_seconds']:.2f} 秒：默认门槛保留 {before['saved_events']} 条产品证据，其中暗裂砖 {before['alarm_class_counts'].get('dark_crack', 0)} 条；低门槛保留 {after['saved_events']} 条，其中暗裂砖 {after['alarm_class_counts'].get('dark_crack', 0)} 条。自动证据均为完整瓷砖最佳帧，三层 CRC、重建像素 CRC、离线掩码/区域/面积一致，相关错误增量为 0。照片属于开发回归，重复合成素材不能当作工厂准确率；本次未新增人工外接显示器目视验收。

另一个弱阈值候选被拒绝：历史裂纹像素精确率为 {rejected['summary']['candidate']['pixel_precision']:.3%}，低于预先规定的 {declaration['gates']['min_crack_pixel_precision']:.0%} 门槛，没有合入算法。低亮度配方仍需暗背景；不能解决所有暗砖、遮挡、间隙和居中问题。已发现活动采集期间切换配方的参数组合竞争（纯主机复现），本版未修；目前应先暂停、显示明确空台并排空事件后切换。下一步 V1.38 优先修复配置原子快照。

打开 `{R.name}.xpr`；Vitis 工作区 `{W.name}`。使用本版 `启动以太网工作站.bat`。完整证据索引在 `reports/v137/validation_summary.json`；受控暗砖证据 PNG 随测试目录保留，不依赖运行中的存档库。回退工程 V1.36 保持不变；轻量备份 `{Path(plan['backup']).as_posix()}`。本版仅保留简短摘要，后续批量汇总报告。
'''
    plan.update(phase='VALIDATED_BOARD', scope='PL_ARM_HOST_LOW_LUMINANCE_PRODUCT_GATE',
                hardware='Fresh V1.37 routed BIT/XSA and rebuilt ARM ELF; matched descriptor ABI 0x54465337; physical input/capture/TCP validation completed',
                active_recipe_switch_limit='Pause plus explicit empty source/drain required; active tuple race planned for V1.38, not fixed here')
    save(O / 'validation_summary.json', summary)
    (R / 'README.md').write_text(readme, encoding='utf-8')
    save(R / 'ITERATION_PLAN.json', plan)
    # The validated benchmark HTML is deliberately not rewritten by sealing.
    sources = {}
    for folder in ('rtl', 'constraints', 'ip_repo', 'models', 'scripts', 'sim', 'host', 'diagnostics', W.name + '/ethernet_sources', 'data/dark_gate'):
        for path in files_under(R / folder):
            if path.suffix not in ('.pid', '.log', '.pyc', '.wdb') and path.name not in ('player_status.json', 'player_instance.json', 'display_command.txt'):
                sources[path.relative_to(R).as_posix()] = sha(path)
    sources['data/real_tiles/hdmi_manifest.json'] = sha(R / 'data/real_tiles/hdmi_manifest.json')
    for path in W.iterdir():
        if path.is_file() and path.suffix in ('.py', '.tcl', '.bat'):
            sources[path.relative_to(R).as_posix()] = sha(path)
    # Explicit meaningful report directories; generated simulation trees, WDB,
    # binaries, runtime images and review_records are not sealed as source/proof.
    proof_paths = {R / 'README.md', R / 'ITERATION_PLAN.json', R / 'reports/programmed_v137.json'}
    proof_paths.update(R / 'reports' / name for name in hardware['reports_sha256'])
    proof_suffixes = {'.json', '.log', '.csv', '.rpt', '.txt', '.diff', '.xdc'}
    proof_paths.update(p for p in O.iterdir() if p.is_file() and p.suffix in proof_suffixes)
    directories = ('product_gate_experiment', 'product_gate_validation', 'capture_regression', 'product_gate_native',
                   'native_sg', 'native_stream', 'preview_tcp_load', 'storage_rollback_process', 'native_stimulus',
                   'weak_candidate', 'next_iteration_analysis', 'real_board')
    for name in directories:
        proof_paths.update(p for p in (O / name).iterdir() if p.is_file()
                           and (p.suffix in proof_suffixes or (name == 'real_board' and p.suffix == '.png')
                                or (name == 'next_iteration_analysis' and p.suffix == '.py')))
    proof_paths.add(O / 'dark_gate_board/summary.json')
    proof_paths.update(p for p in files_under(Path(dark['run_directory'])) if p.suffix in {'.json', '.png'})
    proofs = {p.relative_to(R).as_posix(): sha(p) for p in sorted(proof_paths)}
    # Refresh only seal-authored files; all executed input hashes came from the
    # records checked above, not from a claim that a test was rerun at seal time.
    for name in ('ITERATION_PLAN.json', 'reports/v137/validation_summary.json'):
        BOUND[str((R / name).resolve())] = sha(R / name)
    size = sum(path.stat().st_size for path in files_under(R))
    manifest = dict(version=VERSION, status=STATUS, created_at=summary['completed_at'], baseline=str(baseline),
        baseline_manifest_sha256=plan['baseline_manifest_sha256'], backup=plan['backup'], backup_sha256=plan['backup_sha256'],
        hardware_revision='Fresh V1.37 PL/ARM', artifacts_sha256=artifacts,
        source_sha256=sources, proof_sha256=proofs, executed_input_output_sha256=BOUND,
        hash_scope='External historical inputs and specifically checked generated outputs are hash-bound but not copied into this source/proof set; no runtime database is used.',
        validation=summary, size_bytes=size, size_scope='Logical files excluding linked directories, runtime and review_records; not full physical disk usage',
        report='README.md', limits=limits)
    save(R / 'DELIVERY_MANIFEST.json', manifest)
    i, j = old_index.index('更新：'), old_index.index('## 当前产品')
    text = old_index[:i] + f'更新：{datetime.datetime.now().astimezone().isoformat()}\n\n最新实板验收：**V1.37**。可选暗色瓷砖产品门槛、新 PL/ARM、默认 50 图与合成连续运动对照通过；裂纹检测算法保持原样。只保留逐版摘要，批量后汇总报告。\n\n' + old_index[j:]
    text = '\n'.join(line for line in text.split('\n') if not line.startswith('| V1.37 |'))
    text = text.replace('## 尚在进行', f'| V1.37 | 可选低亮度产品门槛、逐帧配置锁存、新描述 ABI 与暗砖留图对照 | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行', 1)
    i, j = text.index('## 尚在进行'), text.index('## 回退和空间')
    text = text[:i] + '## 尚在进行\n\nV1.37 已封存。V1.38 优先修复活动采集期间配方参数组合竞争；本版需暂停并用明确空台排空后切换。降低弱阈值候选因精确率门禁失败已拒绝。新的暗砖对照为重复合成素材，未新增人工外接显示器目视确认。\n\n' + text[j:]
    index.write_text(text, encoding='utf-8')
    print(json.dumps(dict(version=VERSION, status=STATUS, boot_id=boot, unit_tests=host['unit_tests']['count'], source_files=len(sources), proof_files=len(proofs))))


if __name__ == '__main__':
    main()
