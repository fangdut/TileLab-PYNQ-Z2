"""Validate fixed RTL product lifecycle with invalid observations without board operations."""
from pathlib import Path
import csv,hashlib,json,subprocess,time
R=Path(__file__).resolve().parents[1];O=R/'reports/v142/tracker_invalid_fixed'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert R.name=='pynq_z2_tile_v1_53'
    O.mkdir(parents=True,exist_ok=True);assert not (O/'summary.json').exists()
    names=['rtl/product_tracker.v','sim/tb_tracker_invalid_fixed.sv','scripts/tracker_invalid_fixed.tcl','scripts/run_tracker_invalid_fixed.py','scripts/product_gate_no_wave.tcl']
    h={n:sha(R/n) for n in names};assert h['rtl/product_tracker.v']!=sha(R.parent/'pynq_z2_tile_v1_41/rtl/product_tracker.v')
    result=dict(passed=False,fixed_policy_validated=False,source_sha256=h,hardware_used=False,
        scope='Production product_tracker RTL, injected invalid observation metadata; module-only policy validation; full capture/hardware tests remain required')
    (O/'provenance.json').write_text(json.dumps(result,indent=2)+'\n');start=time.monotonic()
    try:
        cmd=['D:/2025.2/Vivado/bin/vivado.bat','-mode','batch','-source',str(R/'scripts/tracker_invalid_fixed.tcl'),'-log',str(O/'vivado.log'),'-journal',str(O/'vivado.jou'),'-notrace']
        with (O/'runner.log').open('w') as f:proc=subprocess.run(cmd,cwd=O,stdout=f,stderr=subprocess.STDOUT)
        assert proc.returncode==0
        log=(O/'simulate.log').read_text();assert 'PASS V142 FIXED:' in log and 'Fatal:' not in log
        rows=list(csv.DictReader((O/'observations.csv').open()))
        assert len(rows)==20 and [int(r['product_id']) for r in rows]==[0,1,1,1,1,1,1,1,1,1,1,1,0,2,2,2,2,2,0,3]
        assert sum(bool(int(r['flags'],16)&2) for r in rows)==3
        assert sum(bool(int(r['flags'],16)&4) for r in rows)==2
        assert sum(bool(int(r['flags'],16)&8) for r in rows)==5
        assert all(int(r['flags'],16)==0 for r in rows if int(r['region_status'],16)&0x80000000)
        assert h=={n:sha(R/n) for n in names}
        result.update(passed=True,fixed_policy_validated=True,observations=rows,source_unchanged=True,
            proof_sha256={n:sha(O/n) for n in ('simulate.log','observations.csv','runner.log','provenance.json')})
    finally:
        result['run_seconds']=time.monotonic()-start;(O/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,fixed_policy_validated=True,observations=len(rows))))
if __name__=='__main__':main()
