"""Bind completed validation and source inputs before the first full build."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, json, re

R=Path(__file__).resolve().parents[1];O=R/'reports/v142'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,value):p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def main():
    assert R.name=='pynq_z2_tile_v1_53'
    assert not (R/(R.name+'.xpr')).exists(), 'Evidence must precede full build'
    for name in ('tracker_invalid_fixed','tracker_capture_invalid','capture_regression',
                 'product_gate_validation','porch_fixed'):
        assert load(O/name/'summary.json')['passed'],name
    assert load(O/'host_validation.json')['passed']
    folder=O/'scheduling_boundaries'
    text=(folder/'simulate.log').read_text()
    assert 'Fatal:' not in text
    match=re.search(r'PASS V141 scheduling boundaries[^\n]*',text)
    assert match,text[-1000:]
    print(match[0])
    rows=list(csv.DictReader((folder/'boundary_packets.csv').open(newline='')))
    # The SV bench checks all22 frame epochs and16 decision pulses, including
    # two reset-aborted captures. The CSV independently counts completed packets.
    totals={n:int(v) for n,v in re.findall(r'(packets|stalls|decisions|epochs)=(\d+)',match[0])}
    assert totals==dict(packets=14,stalls=36,decisions=16,epochs=22),totals
    assert len(rows)==totals['packets'] and sum(int(row['invalid']) for row in rows)==1
    names=['rtl/frame_capture_sg.v','rtl/product_tracker.v','sim/tb_capture_scheduling_v141.sv',
           'scripts/test_capture_scheduling_v142.tcl','scripts/product_gate_no_wave.tcl']
    save(folder/'summary.json',dict(passed=True,revision='V1.42',
        scope='Compact injected-region scheduling boundaries; no actual region engine or hardware',
        epochs=totals['epochs'],packets=len(rows),invalid_packets=1,held_axis_cycles=totals['stalls'],product_decisions=totals['decisions'],
        reset_aborted_packets=2,simulator_pass_marker=match[0],
        source_sha256_after={n:sha(R/n) for n in names},
        hash_timing='Collected after successful simulation; no pre-run hash snapshot claimed',
        proof_sha256={n:sha(folder/n) for n in ('simulate.log','boundary_packets.csv')}))
    native=load(O/'product_gate_native/summary.json');assert native['passed'] and native['checks']==33910
    save(O/'firmware_native_summary.json',dict(passed=True,
        scope='Current native C gate/application/protocol suite only; firmware logic unchanged except version/banner. No ARM or board execution.',
        source_sha256=native['source_sha256'],proof_sha256={'product_gate_native/summary.json':sha(O/'product_gate_native/summary.json')},
        counts=dict(assertions=native['checks'],**native['results'])))
    sources=[]
    for folder in ('rtl','constraints','ip_repo'):
        sources.extend(p for p in (R/folder).rglob('*') if p.is_file())
    sources.extend(R/n for n in ('scripts/create_project.tcl','scripts/add_capture.tcl','scripts/ps7_preset.tcl'))
    save(O/'build_inputs.json',dict(revision='V1.42',stage='PRE_FULL_BUILD',created_at=datetime.now(timezone.utc).isoformat(),
        source_sha256={p.relative_to(R).as_posix():sha(p) for p in sources}))
    plan=load(R/'ITERATION_PLAN.json');plan.update(phase='RTL_PASSED_READY_FULL_BUILD',scope='PL_INVALID_OBSERVATION_TRACKING')
    save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase='RTL_PASSED_READY_FULL_BUILD',updated_at=datetime.now(timezone.utc).isoformat(),
        live_station='V1.41 real_video preview-only2fps; no V142 programming yet',
        pending=['Fresh Vivado route and reset/CDC/timing audit','Fresh matching Vitis ELF audit',
                 'Program and run bounded dense, real-photo and motion tests','Seal V142, then backup before next iteration'],
        policy='No formal per-version report; preserve concise README and evidence'))
    print(json.dumps(dict(passed=True,build_sources=len(sources))))

if __name__=='__main__':main()
