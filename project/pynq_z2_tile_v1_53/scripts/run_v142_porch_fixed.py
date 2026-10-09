"""Validate fixed capture scheduling at realistic porch timing; compare sealed baseline."""
from pathlib import Path
import csv
import datetime
import hashlib
import json
import struct
import subprocess
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/v142/porch_fixed'
SOURCES = ['rtl/region_grid.v', 'rtl/frame_capture_sg.v', 'rtl/product_tracker.v',
           'sim/tb_capture_region_porch_fixed.sv', 'scripts/run_v142_porch_fixed.py',
           'scripts/run_v142_porch_fixed.tcl', 'scripts/product_gate_no_wave.tcl']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(name):
    with (OUT / name).open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def main():
    assert ROOT.name == 'pynq_z2_tile_v1_53'
    OUT.mkdir(parents=True, exist_ok=True)
    # Do not replace a completed baseline proof after any production edits.
    assert not (OUT / 'summary.json').exists(), 'Baseline already executed; preserve it'
    before = {name: sha(ROOT / name) for name in SOURCES}
    baseline = Path('D:/Vivado/pynq_z2_tile_v1_41')
    inherited = {name: sha(baseline / name) for name in SOURCES[:3]}
    assert all(before[name] == value for name, value in inherited.items() if name!='rtl/product_tracker.v')
    assert before['rtl/product_tracker.v']!=inherited['rtl/product_tracker.v']
    result = dict(passed=False, fixed_schedule_validated=False, revision='V1.42',
        started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Unmodified V141 region_grid/frame_capture_sg with V142 invalid-observation product_tracker, synthetic mask raster, AXIS ready=1',
        source_sha256=before, baseline_v141_rtl_sha256=inherited,
        production_modified=True, hardware_used=False,
        limitations=['No real HDMI measurement, detector accuracy, DMA or ARM/network test.',
            'Clock-edge spacing is 13.468 ns; authoritative scheduling measurements are integer pixel-clock counts.',
            'ROI case is a deliberately injected 36x18-cell rectangle, not a detector output from the physical noise image.'])
    (OUT / 'provenance.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    start = time.monotonic()
    try:
        command = ['D:/2025.2/Vivado/bin/vivado.bat', '-mode', 'batch', '-source',
                   str(ROOT / 'scripts/run_v142_porch_fixed.tcl'), '-log',
                   str(OUT / 'vivado.log'), '-journal', str(OUT / 'vivado.jou'), '-notrace']
        with (OUT / 'runner.log').open('w', encoding='utf-8') as stream:
            process = subprocess.run(command, cwd=OUT, stdout=stream, stderr=subprocess.STDOUT)
        result['vivado_exit_code'] = process.returncode
        assert process.returncode == 0, 'See runner.log and simulate.log'
        after = {name: sha(ROOT / name) for name in SOURCES}
        result['sources_unchanged'] = before == after
        assert before == after
        packets, regions, boundaries = rows('packets.csv'), rows('regions.csv'), rows('boundaries.csv')
        descriptors = {}
        for row in rows('descriptors.csv'):
            descriptors.setdefault(int(row['seq']), {})[int(row['index'])] = int(row['word'], 16)
        # A second CRC implementation in Python rechecks complete descriptor words.
        for packet in packets:
            seq = int(packet['seq'])
            words = descriptors[seq]
            assert set(words) == set(range(40))
            raw = b''.join(struct.pack('<I', 0 if n == 8 else words[n]) for n in range(40))
            assert zlib.crc32(raw) == words[8] == int(packet['descriptor_crc'], 16)
            case_id = int(packet['case_id'])
            crc = 0
            for y in range(720):
                data = bytearray()
                for x in range(1280):
                    mask = (case_id == 2 or (case_id == 1 and 320 <= x < 352 and 320 <= y < 352)
                            or (case_id == 3 and 64 <= x < 1216 and 64 <= y < 640))
                    data.extend((90, 90, 90, int(mask)))
                crc = zlib.crc32(data, crc)
            assert crc == words[1] == int(packet['pixel_crc'], 16)
            assert int(packet['words']) == 921640 and int(packet['bytes']) == 3686560
        assert [int(p['seq']) for p in packets] == list(range(1,13))
        assert len(regions) == len(boundaries) == 12
        assert sum(int(p['capture_bad']) for p in packets) == 0
        assert all(int(p['capture_bad']) == int(p['region_bad']) for p in packets)
        names = ['empty', 'sparse_one_cell', 'dense_920_cells', 'roi_648_cells']
        cases = []
        for index, name in enumerate(names):
            selected = [r for r in regions if int(r['case_id']) == index]
            case_packets = [p for p in packets if int(p['case_id']) == index]
            late = [int(r['published_cycle']) - int(r['next_vs_cycle']) for r in selected]
            cases.append(dict(name=name, input_frames=len(selected), packets=len(case_packets),
                invalid_packets=sum(int(p['capture_bad']) for p in case_packets),
                region_latency_cycles=sorted({int(r['latency_cycles']) for r in selected}),
                last_de_to_vs_cycles=sorted({int(r['next_vs_cycle']) - int(r['last_de_fall_cycle']) for r in selected}),
                region_publication_after_vs_cycles=late, region_status_all_valid=all(int(r['status'], 16) < 0x80000000 for r in selected)))
            assert all((delta > 0) == (index >= 2) for delta in late)
        result.update(passed=True, fixed_schedule_validated=True, cases=cases,
            input_frames=12, full_packets=12, invalid_packets=0, skipped_input_frames=0,
            pixel_crc_checks=12, descriptor_crc_checks=12, python_crc_cross_checks=24,
            packet_sequences=[int(p['seq']) for p in packets],
            conclusion='Both dense and 648-cell regions still publish after next VS before next DE; all twelve complete packets now preserve consecutive sequence, pixel CRC and descriptor CRC without invalid flags.')
        proof_names = ['packets.csv', 'regions.csv', 'boundaries.csv', 'descriptors.csv', 'simulate.log', 'runner.log', 'provenance.json']
        result['proof_sha256'] = {name: sha(OUT / name) for name in proof_names}
        result['wave_files'] = [{'path':str(p.relative_to(OUT)), 'bytes':p.stat().st_size} for p in OUT.rglob('*.wdb')]
        assert all(item['bytes'] < 1000000 for item in result['wave_files']), 'Unexpected recorded waveform growth'
    except Exception as error:
        result.update(passed=False, error=f'{type(error).__name__}: {error}')
        raise
    finally:
        result['run_seconds'] = round(time.monotonic() - start, 3)
        result['source_sha256_after'] = {name:sha(ROOT / name) for name in SOURCES}
        result['sources_unchanged'] = result['source_sha256_after'] == before
        (OUT / ('summary.json' if result['passed'] else 'failed_attempt.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
