"""Real process-exit and independent-process archive-publication checks.

Fixtures are isolated below reports/v133/save_process_exit. This tests abrupt
Python process termination with the OS/storage stack still running. It is NOT
a power-loss, filesystem durability, network ACK, or physical-board test.
Run with the project's Python; no station or hardware connection is opened.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host'))
import numpy as np
import workstation
from workstation import Records, png
from confirmation_journal import IDENTITY_FIELDS

EXIT_CODE = 73
ENDPOINT = 'test-only://save-process-exit/no-network'
STAGES = ('after_first_png', 'after_second_png', 'after_events_insert', 'after_commit')
FRAME = dict(boot_id=133, event_id=91, frame_id=733, product_id=5,
             selection='FPGA_PRODUCT_BEST_FRAME', candidate_pixels=12,
             boxes=[[2, 3, 5, 6]], region_areas=[12], config_word=90,
             selection_center_distance_x2=4, pixel_crc32=0x12345678,
             recovery_generation=2)
TARGET = 'tile_133_5'
BASELINE = dict(FRAME, event_id=90, frame_id=732, product_id=4)
BASELINE_KEY = 'tile_133_4'


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def fixture_pixels(changed=False):
    yy, xx = np.indices((16, 24))
    image = np.stack(((xx * 7 + 30) % 256, (yy * 9 + 40) % 256,
                      (xx + yy * 3 + 50) % 256), axis=-1).astype(np.uint8)
    if changed:
        image[4:8, 5:10] ^= np.uint8(127)
    mask = np.zeros((16, 24), np.uint8)
    mask[3:7, 2:5] = 255
    return png(image), png(mask)


def pending_identity(pending):
    return dict(record_id=pending['record_id'], endpoint=pending['endpoint'],
                frame={key: pending['frame'].get(key) for key in IDENTITY_FIELDS})


def wait_file(path, processes=(), timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if Path(path).exists():
            return
        for process in processes:
            if process.poll() is not None:
                raise AssertionError(f'Child {process.pid} exited early with {process.returncode}, waiting for {path}')
        time.sleep(.01)
    raise TimeoutError(f'Timed out waiting for {path}')


def checkpoint(directory, stage):
    write_json(directory / 'exit_checkpoint.json',
               dict(stage=stage, pid=os.getpid(), method='os._exit', code=EXIT_CODE))
    os._exit(EXIT_CODE)


class ExitConnection:
    """Observe actual SQLite operations without modifying production sources."""
    def __init__(self, connection, directory, stage):
        self.connection, self.directory, self.stage = connection, directory, stage

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def execute(self, statement, parameters=()):
        result = self.connection.execute(statement, parameters)
        if self.stage == 'after_events_insert' and statement.startswith('INSERT INTO events '):
            checkpoint(self.directory, self.stage)
        return result

    def commit(self):
        result = self.connection.commit()
        if self.stage == 'after_commit':
            checkpoint(self.directory, self.stage)
        return result


def worker(directory, mode):
    directory = Path(directory)
    record = Records(directory)
    image, mask = fixture_pixels(changed=(mode == 'race_loser'))
    real_atomic = workstation.atomic
    if mode in STAGES:
        count = 0
        def atomic_with_exit(path, data):
            nonlocal count
            real_atomic(path, data)
            count += 1
            if (mode == 'after_first_png' and count == 1) or (mode == 'after_second_png' and count == 2):
                checkpoint(directory, mode)
        workstation.atomic = atomic_with_exit
        proxy = ExitConnection(record.db, directory, mode)
        record.db = proxy
        record.confirmations.db = proxy
        record.save(FRAME, image, mask, 'isolated_process_exit_test', ENDPOINT)
        raise AssertionError(f'Fault checkpoint was not reached: {mode}')

    assert mode in ('race_winner', 'race_loser'), mode
    # Both SQLite connections/schema setup complete before either save starts.
    record.db.execute('PRAGMA busy_timeout=15000')
    write_json(directory / f'{mode}_initialized.json', dict(pid=os.getpid()))
    wait_file(directory / f'{mode}_start.json')
    def trace(statement):
        if statement == 'BEGIN IMMEDIATE':
            write_json(directory / f'{mode}_begin_attempted.json', dict(pid=os.getpid()))
    record.db.set_trace_callback(trace)
    if mode == 'race_winner':
        count = 0
        def atomic_with_barrier(path, data):
            nonlocal count
            real_atomic(path, data)
            count += 1
            if count == 1:
                write_json(directory / 'winner_first_png_published.json', dict(pid=os.getpid()))
                wait_file(directory / 'release_winner.json')
        workstation.atomic = atomic_with_barrier
    try:
        key = record.save(FRAME, image, mask, 'isolated_two_process_test', ENDPOINT)
        outcome = dict(status='saved', key=key)
    except ValueError as error:
        outcome = dict(status='rejected', error=str(error), type=type(error).__name__)
    finally:
        record.db.close()
    write_json(directory / f'{mode}_outcome.json', dict(outcome, pid=os.getpid()))


def seed(directory):
    directory.mkdir(parents=True)
    record = Records(directory)
    image, mask = fixture_pixels()
    record.save(BASELINE, image, mask, 'preexisting_human_review_fixture')
    record.review(BASELINE_KEY, 'confirmed_crack', 'Existing reviewed evidence must remain unchanged.', 0)
    before = baseline_snapshot(record)
    record.db.close()
    return before


def baseline_snapshot(record):
    return dict(row=record.get(BASELINE_KEY),
                image_sha256=hashlib.sha256(record.read_image(BASELINE_KEY)[0]).hexdigest(),
                mask_sha256=hashlib.sha256(record.read_image(BASELINE_KEY, True)[0]).hexdigest())


def expected_identity():
    return dict(record_id=TARGET, endpoint=ENDPOINT,
                frame={key: FRAME.get(key) for key in IDENTITY_FIELDS})


def check_integrity(record):
    assert record.db.execute('PRAGMA integrity_check').fetchone() == ('ok',)


def exit_case(run_dir, stage):
    directory = run_dir / stage
    before = seed(directory)
    child = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).resolve()),
                            '--worker', stage, '--directory', str(directory)],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    (directory / 'child.log').write_bytes(child.stdout)
    assert child.returncode == EXIT_CODE, (stage, child.returncode, child.stdout.decode('utf-8', 'replace'))
    observed = json.loads((directory / 'exit_checkpoint.json').read_text(encoding='utf-8'))
    assert observed['stage'] == stage
    record = Records(directory)
    try:
        check_integrity(record)
        assert baseline_snapshot(record) == before
        rows = record.db.execute('SELECT COUNT(*) FROM events WHERE id=?', (TARGET,)).fetchone()[0]
        pending = record.confirmations.pending()
        committed = stage == 'after_commit'
        assert rows == int(committed), (stage, rows)
        if committed:
            assert pending_identity(pending) == expected_identity()
            assert record.summary()['total'] == 2
        else:
            assert pending is None
            assert record.summary()['total'] == 1
            try:
                record.read_image(TARGET)
            except ValueError as error:
                assert str(error) == 'Record not found'
            else:
                raise AssertionError('An uncommitted orphan became readable as archive evidence')
        assert record.confirmations.history() == []
        files_before_retry = sorted(path.name for path in record.dir.glob(TARGET + '*.png'))
        # A real restart reclaims the SQLite writer lock. It may overwrite
        # unreferenced same-key PNGs, but never a committed reviewed event.
        image, mask = fixture_pixels()
        assert record.save(FRAME, image, mask, 'isolated_process_exit_test', ENDPOINT) == TARGET
        assert record.summary()['total'] == 2
        assert record.read_image(TARGET)[0] == image
        assert record.read_image(TARGET, True)[0] == mask
        after_pending = record.confirmations.pending()
        assert pending_identity(after_pending) == expected_identity()
        if committed:
            assert after_pending == pending  # preserves even journal creation time
        assert baseline_snapshot(record) == before
        check_integrity(record)
        return dict(stage=stage, passed=True, exit_code=child.returncode,
                    checkpoint=observed, committed_before_retry=committed,
                    target_rows_before_retry=rows, pending_before_retry=bool(pending),
                    unreferenced_files_before_retry=[] if committed else files_before_retry,
                    existing_human_review_and_hashes_unchanged=True,
                    retry_idempotent=True, pending_identity=expected_identity(),
                    sqlite_integrity_check='ok', network_ack_sent=False)
    finally:
        record.db.close()


def race_case(run_dir):
    directory = run_dir / 'two_process_conflict'
    before = seed(directory)
    children, logs = {}, []
    try:
        for mode in ('race_winner', 'race_loser'):
            log = (directory / f'{mode}.log').open('wb')
            logs.append(log)
            children[mode] = subprocess.Popen(
                [sys.executable, '-X', 'utf8', str(Path(__file__).resolve()),
                 '--worker', mode, '--directory', str(directory)], stdout=log, stderr=subprocess.STDOUT)
        processes = list(children.values())
        for mode in children:
            wait_file(directory / f'{mode}_initialized.json', processes)
        write_json(directory / 'race_winner_start.json', dict(start=True))
        wait_file(directory / 'winner_first_png_published.json', processes)
        write_json(directory / 'race_loser_start.json', dict(start=True))
        wait_file(directory / 'race_loser_begin_attempted.json', processes)
        time.sleep(.15)
        assert children['race_loser'].poll() is None
        assert not (directory / 'race_loser_outcome.json').exists()
        assert (directory / 'review_records' / (TARGET + '.png')).read_bytes() == fixture_pixels()[0]
        write_json(directory / 'release_winner.json', dict(release=True))
        for child in children.values():
            assert child.wait(timeout=20) == 0
        outcomes = {mode: json.loads((directory / f'{mode}_outcome.json').read_text(encoding='utf-8')) for mode in children}
        assert outcomes['race_winner']['status'] == 'saved'
        assert outcomes['race_loser']['status'] == 'rejected'
        assert 'different pixels' in outcomes['race_loser']['error']
        record = Records(directory)
        try:
            assert baseline_snapshot(record) == before
            assert record.summary()['total'] == 2
            image, mask = fixture_pixels()
            assert record.read_image(TARGET)[0] == image
            assert record.read_image(TARGET, True)[0] == mask
            assert pending_identity(record.confirmations.pending()) == expected_identity()
            check_integrity(record)
        finally:
            record.db.close()
        return dict(passed=True, outcomes=outcomes, loser_blocked_while_first_writer_published=True,
                    winning_png_and_mask_unchanged=True, existing_review_unchanged=True,
                    committed_target_rows=1, pending_identity=expected_identity(),
                    sqlite_integrity_check='ok', network_ack_sent=False)
    finally:
        # Stop only child PIDs started by this test, never services/hardware tools.
        for child in children.values():
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
        for log in logs:
            log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', choices=(*STAGES, 'race_winner', 'race_loser'))
    parser.add_argument('--directory', type=Path)
    args = parser.parse_args()
    if args.worker:
        if args.directory is None:
            parser.error('--worker requires --directory')
        report_root = (ROOT / 'reports/v133/save_process_exit').resolve()
        candidate = args.directory.resolve()
        if not candidate.is_relative_to(report_root):
            parser.error('Worker directory must be inside the isolated report root')
        worker(candidate, args.worker)
        return
    report_root = ROOT / 'reports/v133/save_process_exit'
    run_dir = report_root / ('run_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
    run_dir.mkdir(parents=True)
    summary = dict(passed=False, started_utc=datetime.now(timezone.utc).isoformat(),
                   run_directory=str(run_dir), python=sys.version,
                   scope='Isolated real child-process termination and two-process SQLite/file publication conflict.',
                   limitation='Not a physical power-loss, filesystem durability, board, or network ACK test; orphan PNGs remain until same-key retry.',
                   source_sha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                  for name in ('host/workstation.py', 'host/confirmation_journal.py',
                                               'scripts/test_save_process_exit.py')},
                   exit_cases=[])
    try:
        for stage in STAGES:
            summary['exit_cases'].append(exit_case(run_dir, stage))
        summary['two_process_conflict'] = race_case(run_dir)
        summary['passed'] = True
    except Exception:
        summary['error'] = traceback.format_exc()
        raise
    finally:
        summary['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(run_dir / 'summary.json', summary)
        write_json(report_root / 'summary.json', summary)
    print(json.dumps(dict(passed=True, abrupt_exit_stages=len(STAGES), two_process_conflict=True,
                          summary=str(report_root / 'summary.json')), ensure_ascii=False))


if __name__ == '__main__':
    main()
