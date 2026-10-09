"""Draft, bounded HTTP inventory comparison; never connects to port 8770.

Each case imports one supplied project's real Station/Records/HTTP handler in
its own child process, with bytecode disabled. Each child owns a newly-created
temporary fixture and removes only that exact directory after use. Reports go
below --output-root. There is no capture bridge, camera, FPGA or network peer.
Three local clients poll an ephemeral loopback HTTP server at one request per
second for ten seconds. A candidate forced-fresh case bypasses only its display
cache in the fixture instance, preserving the production inventory algorithm.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve()
WINDOWS = 3
SECONDS = 10
ROWS = 1000
FIXTURE_FILES = 6000


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distributions(values):
    ordered = sorted(values)
    return dict(count=len(ordered), min=min(ordered), median=statistics.median(ordered),
                p95=ordered[max(0, math.ceil(len(ordered)*.95)-1)], max=max(ordered),
                sum=sum(ordered))


def source_hashes(root):
    return {name:sha(root/name) for name in ('host/workstation.py','host/archive_inventory.py')}


class ScanCounter:
    def __init__(self, module):
        self.lock = threading.Lock()
        self.calls = []
        self.real = module.inventory
        module.inventory = self.counted

    def counted(self, directory, record_ids, *args, **kwargs):
        start = time.perf_counter()
        outcome = None
        try:
            result = self.real(directory, record_ids, *args, **kwargs)
            outcome = dict(file_count=result['file_count'], scan_complete=result['scan_complete'])
            return result
        finally:
            with self.lock:
                self.calls.append(dict(directory=str(directory), seconds=time.perf_counter()-start,
                                       result=outcome, thread=threading.get_ident()))

    def snapshot(self):
        with self.lock:
            return list(self.calls)


class NoCaptureBridge:
    """Fail if a supposedly paused HTTP benchmark tries to acquire or ACK."""
    def capture(self, *args, **kwargs):
        raise AssertionError('HTTP inventory benchmark must never capture')
    def ack(self, *args, **kwargs):
        raise AssertionError('HTTP inventory benchmark must never ACK')
    def close(self):
        pass


def small_pngs(module):
    import numpy as np
    yy, xx = np.indices((24, 32))
    pixels = np.stack((xx*7, yy*9, (xx+yy)*3), axis=-1).astype(np.uint8)
    return module.png(pixels), module.png(np.zeros((24,32), np.uint8))


def event_frame(index):
    return dict(boot_id=136, event_id=index, frame_id=5000+index, product_id=index,
                selection='FPGA_PRODUCT_BEST_FRAME', candidate_pixels=0, boxes=[], region_areas=[],
                config_word=90, recovery_generation=0, selection_center_distance_x2=0,
                pixel_crc32=123, width=32, height=24)


def seed_scale_fixture(module, directory):
    """Bulk seeding is outside measured HTTP and does not invoke 1000 scans."""
    directory.mkdir(parents=True)
    (directory/'host').mkdir()
    record = module.Records(directory)
    image, mask = small_pngs(module)
    image_sha, mask_sha = hashlib.sha256(image).hexdigest(), hashlib.sha256(mask).hexdigest()
    stamp = '2026-09-29T00:00:00+00:00'
    rows = []
    for index in range(1, ROWS+1):
        key = f'tile_136_{index}'
        (record.dir/(key+'.png')).write_bytes(image)
        (record.dir/(key+'_mask.png')).write_bytes(mask)
        payload = dict(event_frame(index), reason='fixture', origin='ISOLATED_HTTP_TEST',
                       image_sha256=image_sha, mask_sha256=mask_sha)
        rows.append((key, stamp, 'confirmed_crack' if index%4 == 0 else 'pending',
                     f'Preserved fixture review {index}', json.dumps(payload)))
    record.db.executemany('INSERT INTO events VALUES(?,?,?,?,?)', rows)
    record.db.executemany('INSERT INTO review_revisions VALUES(?,?)',
                          [(f'tile_136_{index}', index%7) for index in range(1,ROWS+1)])
    record.db.commit()
    for index in range(FIXTURE_FILES-ROWS*2):
        (record.dir/f'aux_{index:04d}.bin').write_bytes(index.to_bytes(4,'little')*16)
    assert record.summary()['total'] == ROWS
    record.db.close()


def business_snapshot(record):
    tables = {}
    with record.lock:
        for table in ('events','review_revisions','pending_confirmation','confirmation_history'):
            rows = record.db.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall()
            tables[table] = dict(rows=len(rows), sha256=hashlib.sha256(
                json.dumps(rows, ensure_ascii=False, separators=(',',':')).encode()).hexdigest())
    # SQLite WAL/SHM are operational metadata; business row content is compared
    # above. Every fixture PNG/ordinary file is independently hashed here.
    files = {path.name:sha(path) for path in record.dir.iterdir()
             if path.is_file() and not path.name.startswith('inspection.sqlite3')}
    assert len(files) == FIXTURE_FILES
    return dict(tables=tables, files=files,
                png_count=sum(name.endswith('.png') for name in files))


def fresh_save_probe(module, counter, directory, require_snapshot):
    """Separate writes from the immutable 6000-file HTTP benchmark fixture."""
    directory.mkdir(parents=True)
    record = module.Records(directory)
    image, mask = small_pngs(module)
    try:
        has_snapshot = callable(getattr(record, 'storage_snapshot', None))
        assert has_snapshot or not require_snapshot
        if has_snapshot:
            record.storage_snapshot()
        before = len(counter.snapshot())
        record.storage(); record.storage()
        default_fresh_scans = len(counter.snapshot())-before
        assert default_fresh_scans == 2
        writes = []
        for index in range(1, 4):
            if has_snapshot:
                record.storage_snapshot()  # provide a fresh display-cache hit
            start = len(counter.snapshot())
            key = record.save(event_frame(index), image, mask, 'isolated_fresh_admission_probe')
            scans = len(counter.snapshot())-start
            assert scans == 1, ('New-key save must scan exactly once', index, scans)
            assert record.get(key)['frame_id'] == 5000+index
            writes.append(dict(record_id=key, fresh_scans=scans))
        assert record.summary()['total'] == 3
        assert record.confirmations.pending() is None
        return dict(passed=True, storage_default_fresh_scans=default_fresh_scans,
                    new_key_saves=writes, endpoint_or_network_ack_used=False,
                    fixture_directory=str(directory))
    finally:
        record.db.close()


def child_case(source, output, case):
    sys.path.insert(0, str(source/'host'))
    module = importlib.import_module('workstation')
    assert Path(module.__file__).resolve() == (source/'host/workstation.py').resolve()
    counter = ScanCounter(module)
    temporary_parent = Path(tempfile.gettempdir()).resolve()
    fixture_root = Path(tempfile.mkdtemp(prefix='tile_v136_http_',dir=temporary_parent)).resolve()
    try:
        child_case_body(module,counter,source,output,case,fixture_root)
    finally:
        # Only this invocation's newly-created exact path is eligible; never
        # enumerate/delete other temp entries or old approval-blocked leftovers.
        target = fixture_root.resolve()
        assert target.parent == temporary_parent and target.name.startswith('tile_v136_http_')
        attributes = target.lstat()
        assert not stat.S_ISLNK(attributes.st_mode)
        assert not getattr(attributes,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)
        shutil.rmtree(target)
    result_path = output/'result.json'
    result = json.loads(result_path.read_text(encoding='utf-8'))
    result['fixture_cleanup'] = dict(owned_exact_root=str(fixture_root),removed=not fixture_root.exists())
    assert result['fixture_cleanup']['removed']
    write_json(result_path,result)


def child_case_body(module,counter,source,output,case,fixture_root):
    seed_scale_fixture(module, fixture_root/'http_fixture')
    station = module.Station(fixture_root/'http_fixture', NoCaptureBridge())
    server = None
    server_thread = None
    try:
        assert not station.enabled and not station.manual and not station.busy
        candidate = case.startswith('candidate')
        assert callable(getattr(station.records,'storage_snapshot',None)) or not candidate
        if case == 'candidate_forced_fresh':
            # Fixture-instance intervention for a controlled fresh baseline:
            # leave state(), inventory(), SQL, files and HTTP routing unchanged.
            station.records.storage_snapshot = lambda *args, **kwargs: station.records.storage()
        before_business = business_snapshot(station.records)
        server = module.ThreadingHTTPServer(('127.0.0.1', 0), module.handler(station))
        server.daemon_threads = True
        port = server.server_address[1]
        assert port != 8770
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        address = f'http://127.0.0.1:{port}/api/state?limit=24'
        gate = threading.Barrier(WINDOWS+1)
        start_holder = {}
        before_calls = len(counter.snapshot())

        def window(window_id):
            responses = []
            gate.wait(timeout=5)
            start = start_holder['start']
            for tick in range(SECONDS):
                delay = start+tick-time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
                begun = time.perf_counter()
                with urllib.request.urlopen(address, timeout=10) as response:
                    raw = response.read()
                    assert response.status == 200
                elapsed = time.perf_counter()-begun
                body = json.loads(raw)
                assert body['records_total'] == ROWS and body['archive']['total'] == ROWS
                assert len(body['records']) == 24
                assert body['storage']['scan_complete']
                assert not body['enabled'] and not body['busy'] and not body['error']
                storage = body['storage']
                responses.append(dict(window=window_id, tick=tick,
                    request_start_seconds=begun-start, latency_ms=elapsed*1000, response_bytes=len(raw),
                    image_bytes=storage['image_bytes'], auxiliary_bytes=storage['auxiliary_bytes'],
                    file_count=storage['file_count'], snapshot_cached=storage.get('snapshot_cached'),
                    snapshot_age_seconds=storage.get('snapshot_age_seconds'),
                    snapshot_observed_at=storage.get('snapshot_observed_at')))
            return responses

        with ThreadPoolExecutor(max_workers=WINDOWS) as pool:
            futures = [pool.submit(window,index) for index in range(WINDOWS)]
            start_holder['start'] = time.perf_counter()
            gate.wait(timeout=5)
            responses = [response for future in futures for response in future.result(timeout=25)]
            remaining = start_holder['start']+SECONDS-time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
        elapsed = time.perf_counter()-start_holder['start']
        http_calls = counter.snapshot()[before_calls:]
        assert len(responses) == WINDOWS*SECONDS
        if case == 'candidate_native':
            # One or two TTL refreshes are typical; allow a startup boundary,
            # but a scan per HTTP request would categorically fail.
            assert 1 <= len(http_calls) <= 3, len(http_calls)
            assert sum(response['snapshot_cached'] is True for response in responses) >= 24
        else:
            assert len(http_calls) == len(responses), (case, len(http_calls), len(responses))
        assert business_snapshot(station.records) == before_business
        assert station.records.db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert not station.captures and not station.records.confirmations.pending()
        summary = dict(passed=True, case=case, source_root=str(source),
            source_sha256=source_hashes(source), fixture_business_rows=ROWS,
            fixture_ordinary_files_excluding_database=FIXTURE_FILES,
            fixture_pngs=ROWS*2, concurrent_windows=WINDOWS,
            requests_per_window=SECONDS, requested_window_seconds=SECONDS,
            elapsed_seconds=elapsed, http_requests=len(responses),
            http_latency_ms=distributions([item['latency_ms'] for item in responses]),
            inventory_scans=len(http_calls), inventory_duration_ms=distributions([item['seconds']*1000 for item in http_calls]),
            response_bytes=sum(item['response_bytes'] for item in responses),
            unchanged_business_tables=before_business['tables'],
            all_fixture_file_hashes_unchanged=True, all_fixture_files_before=before_business['files'],
            sqlite_integrity_check='ok', actual_loopback_port=port,
            snapshots=sorted(responses,key=lambda item:(item['tick'],item['window'])),
            inventory_calls=http_calls, no_hardware_or_capture=True,
            python_bytecode_disabled=sys.dont_write_bytecode)
        if case != 'candidate_forced_fresh':
            summary['independent_fresh_save_probe'] = fresh_save_probe(
                module, counter, fixture_root/'write_fixture', require_snapshot=candidate)
        write_json(output/'result.json', summary)
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if server_thread is not None:
            server_thread.join(3)
        station.exit = True
        station.worker.join(3)
        station.records.db.close()
        assert not station.worker.is_alive()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-root', type=Path)
    parser.add_argument('--candidate-root', type=Path)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--child-source', type=Path)
    parser.add_argument('--child-case', choices=('baseline_native','candidate_native','candidate_forced_fresh'))
    args = parser.parse_args()
    output = args.output_root.resolve()
    if args.child_case:
        if args.child_source is None:
            parser.error('Child source required')
        source = args.child_source.resolve()
        if output.is_relative_to(source) and (args.child_case == 'baseline_native' or not output.is_relative_to(source/'reports')):
            parser.error('Never write baseline source; candidate reports are the only allowed in-project output')
        child_case(source,output,args.child_case)
        return
    if args.baseline_root is None or args.candidate_root is None:
        parser.error('Both baseline and candidate roots are required')
    baseline, candidate = args.baseline_root.resolve(), args.candidate_root.resolve()
    for source in (baseline,candidate):
        if not (source/'host/workstation.py').is_file():
            parser.error('Missing workstation source: '+str(source))
        if output.is_relative_to(source) and (source == baseline or not output.is_relative_to(source/'reports')):
            parser.error('Output must be outside baseline and outside candidate source directories')
    run = output/('run_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
    run.mkdir(parents=True)
    hashes_before = {str(source):source_hashes(source) for source in (baseline,candidate)}
    summary = dict(passed=False, started_utc=datetime.now(timezone.utc).isoformat(),
        run_directory=str(run), script_sha256=sha(SCRIPT), cases=[],
        scope='Real loopback HTTP polling and inventory counts over isolated 6000-file/1000-row fixtures.',
        limitations=['No request goes to the real workstation or port 8770.',
            'No FPGA, camera, HDMI, capture or network ACK throughput is measured.',
            'Performance depends on host filesystem/cache/load; exact scan counts are the primary scheduling proof.',
            'Source modules are read-only imports with bytecode disabled; business fixture rows/files are hash-checked.',
            'Forced-fresh changes only the candidate fixture instance display snapshot call, not project source.',
            'Independent small write fixtures test fresh admission semantics; their writes are excluded from HTTP timings.'])
    try:
        for case,source in (('baseline_native',baseline),('candidate_native',candidate),('candidate_forced_fresh',candidate)):
            directory = run/case
            directory.mkdir()
            env = os.environ.copy()
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            command = [sys.executable,'-B','-X','utf8',str(SCRIPT),'--child-source',str(source),
                       '--child-case',case,'--output-root',str(directory)]
            completed = subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,timeout=90)
            (directory/'child.log').write_bytes(completed.stdout)
            assert completed.returncode == 0, completed.stdout.decode('utf-8','replace')
            result = json.loads((directory/'result.json').read_text(encoding='utf-8'))
            summary['cases'].append(result)
            print(json.dumps({key:result[key] for key in ('case','http_requests','inventory_scans','http_latency_ms')}),flush=True)
        assert {str(source):source_hashes(source) for source in (baseline,candidate)} == hashes_before
        baseline_result,cached,fresh = summary['cases']
        summary['comparison'] = dict(
            inventory_scan_reduction_vs_v135_percent=100*(1-cached['inventory_scans']/baseline_result['inventory_scans']),
            inventory_scan_reduction_vs_candidate_fresh_percent=100*(1-cached['inventory_scans']/fresh['inventory_scans']),
            median_http_latency_ms={item['case']:item['http_latency_ms']['median'] for item in summary['cases']},
            exact_business_and_file_hashes_preserved=True, source_hashes_unchanged=True)
        summary['passed'] = True
    except Exception:
        summary['error'] = traceback.format_exc()
        raise
    finally:
        summary['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(run/'summary.json',summary)
        write_json(output/'summary.json',summary)


if __name__ == '__main__':
    main()
