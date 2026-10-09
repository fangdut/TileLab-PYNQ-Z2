"""Isolated multi-process reproduction and regression for archive accounting.

A coordinator keeps Records open while a second real process publishes PNGs
and then os._exit()s or raises through Records.save's rollback. No SQL commit
occurs; SQLite data_version stays unchanged. V1.34 must reproduce stale usage;
V1.37 must inventory all ordinary files and reject a new over-quota event.
All writes stay below this version's reports/v148/storage_rollback_process.
Baseline sources are imported read-only, with Python bytecode disabled.
This is process-failure/rollback testing, not physical-power-loss validation.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
BASELINE_ROOT = ROOT.parent / 'pynq_z2_tile_v1_34'
REPORT_ROOT = ROOT / 'reports/v148/storage_rollback_process'
SCRIPT = Path(__file__).resolve()
EXIT_CODE = 81
STAGES = ('exit_after_first', 'exit_after_second', 'raise_after_first', 'raise_after_second')
BASE_FRAME = dict(boot_id=135, event_id=10, frame_id=900, product_id=100,
                  selection='FPGA_PRODUCT_BEST_FRAME', candidate_pixels=12,
                  boxes=[[1, 2, 3, 5]], region_areas=[12], config_word=90,
                  selection_center_distance_x2=2, pixel_crc32=123,
                  recovery_generation=0)
BASE_KEY = 'tile_135_100'
FAULT_FRAME = dict(BASE_FRAME, event_id=11, frame_id=901, product_id=101)
FAULT_KEY = 'tile_135_101'
NEW_FRAME = dict(BASE_FRAME, event_id=12, frame_id=902, product_id=102)
NEW_KEY = 'tile_135_102'
ENDPOINT = 'test-only://storage-rollback/no-network'


def write_json(path, value):
    with Path(path).open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def load_workstation(source):
    assert sys.dont_write_bytecode
    sys.path.insert(0, str(source / 'host'))
    module = importlib.import_module('workstation')
    assert Path(module.__file__).resolve() == (source / 'host/workstation.py').resolve()
    return module


def child_command(mode, version, directory, stage):
    return [sys.executable, '-B', '-X', 'utf8', str(SCRIPT), '--mode', mode,
            '--version', version, '--directory', str(directory), '--stage', stage]


def child_environment():
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def fixture_pixels(module):
    import numpy as np
    rng = np.random.default_rng(135)
    image = module.png(rng.integers(0, 256, (256, 256, 3), dtype=np.uint8))
    mask = module.png(rng.integers(0, 2, (256, 256), dtype=np.uint8) * 255)
    return image, mask


def write_extra_files(directory):
    archive = directory / 'review_records'
    extra = {
        'interrupted.png.tmp': b'temporary-fixture-' * 8192,
        'diagnostic/nested.bin': b'nested-ordinary-fixture-' * 4096,
        'diagnostic/not_indexed.png': b'nested-png-extension-fixture-' * 1024,
    }
    for relative, data in extra.items():
        path = archive / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    return {name: len(data) for name, data in extra.items()}


def wait_file(path, child, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        if child.poll() is not None:
            raise AssertionError(f'Child {child.pid} exited before checkpoint: {child.returncode}')
        time.sleep(.01)
    raise TimeoutError(str(path))


class PublicationFailure(OSError):
    pass


def worker(module, directory, stage):
    record = module.Records(directory)
    image, mask = fixture_pixels(module)
    real_atomic = module.atomic
    publication_count = 0
    target_count = 1 if stage.endswith('first') else 2
    write_json(directory / 'worker_ready.json', dict(pid=os.getpid(), bytecode_disabled=sys.dont_write_bytecode))
    deadline = time.monotonic() + 15
    while not (directory / 'start_publication.json').exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('Coordinator did not release worker')
        time.sleep(.01)

    def fault_after_publication(path, data):
        nonlocal publication_count
        real_atomic(path, data)
        publication_count += 1
        if publication_count == target_count:
            extras = write_extra_files(directory)
            write_json(directory / 'fault_checkpoint.json',
                       dict(stage=stage, published_pngs=publication_count, extras=extras,
                            pid=os.getpid(), transaction_active=record.db.in_transaction))
            if stage.startswith('exit'):
                os._exit(EXIT_CODE)
            raise PublicationFailure('Injected exception after PNG publication')

    module.atomic = fault_after_publication
    try:
        record.save(FAULT_FRAME, image, mask, 'isolated_fault', ENDPOINT)
    except PublicationFailure:
        assert not record.db.in_transaction
        assert record.summary()['total'] == 1
        assert record.confirmations.pending() is None
        write_json(directory / 'rollback_completed.json', dict(rolled_back=True, published_pngs=publication_count))
    else:
        raise AssertionError('Publication fault not reached')
    finally:
        record.db.close()


def ordinary_inventory(directory):
    # Fixture contains only ordinary local files and directories; no links.
    files = {str(p.relative_to(directory)).replace('\\', '/'): p.stat().st_size
             for p in directory.rglob('*') if p.is_file()}
    return dict(files=files, total=sum(files.values()))


def archive_hashes(directory):
    return {str(p.relative_to(directory)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file() and not p.name.startswith('inspection.sqlite3')}


def old_review(record):
    return dict(row=record.get(BASE_KEY),
                image_sha256=hashlib.sha256(record.read_image(BASE_KEY)[0]).hexdigest(),
                mask_sha256=hashlib.sha256(record.read_image(BASE_KEY, True)[0]).hexdigest())


def coordinator(module, directory, version, stage):
    record = module.Records(directory)
    image, mask = fixture_pixels(module)
    record.save(BASE_FRAME, image, mask, 'already_reviewed_fixture')
    record.review(BASE_KEY, 'confirmed_crack', 'Retain this reviewed original.', 0)
    reviewed_before = old_review(record)
    child = None
    log = (directory / 'worker.log').open('wb')
    try:
        # The long-lived reader exists first. Take its version baseline only
        # after the worker's schema/connection initialization has completed.
        child = subprocess.Popen(child_command('worker', version, directory, stage),
                                 stdout=log, stderr=subprocess.STDOUT, env=child_environment())
        wait_file(directory / 'worker_ready.json', child)
        before = record.storage()
        data_version_before = record.db.execute('PRAGMA data_version').fetchone()[0]
        # Old accounting would admit one additional pair plus its 64 KiB reserve.
        # Uncommitted files will exceed the small extra allowance by far.
        record.max_archive_bytes = before['used_bytes'] + len(image) + len(mask) + 65536 + 16384
        write_json(directory / 'start_publication.json', dict(start=True))
        return_code = child.wait(timeout=20)
        assert return_code == (EXIT_CODE if stage.startswith('exit') else 0), return_code
        assert (directory / 'fault_checkpoint.json').exists()
        if stage.startswith('raise'):
            assert json.loads((directory / 'rollback_completed.json').read_text())['rolled_back']
        data_version_after = record.db.execute('PRAGMA data_version').fetchone()[0]
        assert data_version_after == data_version_before, (data_version_before, data_version_after)
        assert record.summary()['total'] == 1
        assert record.confirmations.pending() is None
        assert old_review(record) == reviewed_before
        filesystem_before = ordinary_inventory(record.dir)
        hashes_before = archive_hashes(record.dir)
        observed = record.storage()
        filesystem_after = ordinary_inventory(record.dir)
        assert filesystem_before == filesystem_after
        assert record.db.execute('PRAGMA data_version').fetchone()[0] == data_version_before
        missing = filesystem_after['total'] - observed['used_bytes']
        expected_unindexed = 1 if stage.endswith('first') else 2
        uncommitted_png_names = [FAULT_KEY+'.png'] + ([FAULT_KEY+'_mask.png'] if expected_unindexed == 2 else [])
        extras = json.loads((directory / 'fault_checkpoint.json').read_text())['extras']
        unaccounted_expected = sum(filesystem_after['files'][name] for name in uncommitted_png_names) + sum(extras.values())
        attempted = False
        rejection = None
        try:
            record.save(NEW_FRAME, image, mask, 'isolated_quota_probe', ENDPOINT)
            attempted = True
        except module.ArchiveCapacityError as error:
            rejection = str(error)
        if version == 'baseline':
            assert missing == unaccounted_expected and missing > 0, (missing, unaccounted_expected)
            assert attempted and rejection is None, 'Old under-count regression was not reproduced'
            assert record.confirmations.pending()['record_id'] == NEW_KEY
            assert ordinary_inventory(record.dir)['total'] > record.max_archive_bytes
        else:
            assert missing == 0, (observed, filesystem_after)
            assert observed['scan_complete'] and observed['scan_issue_count'] == 0
            # Nested PNGs are unindexed too, while their bytes are auxiliary.
            assert observed['unindexed_png_count'] == expected_unindexed + 1
            assert observed['temp_file_count'] == 1
            assert observed['auxiliary_bytes'] == sum(extras.values())
            assert observed['file_count'] == len(filesystem_after['files'])
            assert not attempted and rejection
            assert record.summary()['total'] == 1
            assert record.confirmations.pending() is None
            assert archive_hashes(record.dir) == hashes_before
            assert not (record.dir / (NEW_KEY + '.png')).exists()
            assert not (record.dir / (NEW_KEY + '_mask.png')).exists()
            assert not record.db.in_transaction
            # Existing evidence retries remain possible even when an unrelated
            # orphan consumes the budget. They cannot rewrite the human review.
            assert record.save(BASE_FRAME, image, mask, 'idempotent_retry') == BASE_KEY
            assert archive_hashes(record.dir) == hashes_before
        assert old_review(record) == reviewed_before
        for name, digest in hashes_before.items():
            assert hashlib.sha256((record.dir / name).read_bytes()).hexdigest() == digest
        assert record.db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        result = dict(passed=True, version=version, stage=stage, worker_exit_code=return_code,
                      long_lived_connection_data_version_before=data_version_before,
                      long_lived_connection_data_version_after=data_version_after,
                      unchanged_data_version=True, physical_logical_file_bytes=filesystem_after['total'],
                      reported_used_bytes=observed['used_bytes'], omitted_bytes=missing,
                      expected_old_omission_bytes=unaccounted_expected,
                      storage_before=before, storage_after_fault=observed,
                      measured_files=filesystem_after['files'], max_archive_bytes=record.max_archive_bytes,
                      new_save_accepted=attempted, capacity_rejection=rejection,
                      durable_pending_created_by_probe=attempted,
                      committed_human_review_and_hashes_unchanged=True,
                      uncommitted_files_retained=True, network_ack_sent=False,
                      sqlite_integrity_check='ok', python_bytecode_disabled=True)
        write_json(directory / 'result.json', result)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait(timeout=5)
        log.close()
        record.db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('coordinator', 'worker'))
    parser.add_argument('--version', choices=('baseline', 'current'))
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--stage', choices=STAGES)
    args = parser.parse_args()
    if args.mode:
        if args.version is None or args.directory is None or args.stage is None:
            parser.error('A child mode requires version, directory and stage')
        directory = args.directory.resolve()
        if not directory.is_relative_to(REPORT_ROOT.resolve()):
            parser.error('All test fixtures must be inside the current isolated reports root')
        module = load_workstation(BASELINE_ROOT if args.version == 'baseline' else ROOT)
        if args.mode == 'worker':
            worker(module, directory, args.stage)
        else:
            coordinator(module, directory, args.version, args.stage)
        return
    run = REPORT_ROOT / ('run_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
    run.mkdir(parents=True)
    summary = dict(passed=False, started_utc=datetime.now(timezone.utc).isoformat(),
                   run_directory=str(run), scope='Real process publication failures with a long-lived independent SQLite connection; old-source reproduction and new-source quota regression.',
                   limitations=['Process exit and Python exception rollback are not physical power-loss tests.',
                                'Usage means ordinary-file logical byte lengths, not NTFS allocated clusters.',
                                'No board, station worker, or network ACK transport is started; pending_confirmation is the checked durable ACK intention.',
                                'No fixture or existing evidence is deleted; orphan cleanup is outside this test.'],
                   baseline_read_only_import_bytecode_disabled=True,
                   source_sha256={'baseline/workstation.py':hashlib.sha256((BASELINE_ROOT/'host/workstation.py').read_bytes()).hexdigest(),
                                  'current/workstation.py':hashlib.sha256((ROOT/'host/workstation.py').read_bytes()).hexdigest(),
                                  'test_script':hashlib.sha256(SCRIPT.read_bytes()).hexdigest()}, cases=[])
    inventory_source = ROOT / 'host/archive_inventory.py'
    if inventory_source.exists():
        summary['source_sha256']['current/archive_inventory.py'] = hashlib.sha256(inventory_source.read_bytes()).hexdigest()
    try:
        for version in ('baseline', 'current'):
            for stage in STAGES:
                directory = run / version / stage
                directory.mkdir(parents=True)
                completed = subprocess.run(child_command('coordinator', version, directory, stage),
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           env=child_environment(), timeout=40)
                (directory / 'coordinator.log').write_bytes(completed.stdout)
                assert completed.returncode == 0, completed.stdout.decode('utf-8', 'replace')
                summary['cases'].append(json.loads((directory / 'result.json').read_text(encoding='utf-8')))
        summary['passed'] = True
    except Exception:
        summary['error'] = traceback.format_exc()
        raise
    finally:
        summary['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(run / 'summary.json', summary)
        write_json(REPORT_ROOT / 'summary.json', summary)
    print(json.dumps(dict(passed=True, baseline_reproductions=4, current_regressions=4,
                          summary=str(REPORT_ROOT/'summary.json')), ensure_ascii=False))


if __name__ == '__main__':
    main()
