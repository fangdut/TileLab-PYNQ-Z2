"""Reproduce actual baseline RTL product-ID corruption without board operations."""
from pathlib import Path
import csv,hashlib,json,subprocess,time
R=Path(__file__).resolve().parents[1];O=R/'reports/v142/tracker_invalid_baseline'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert R.name=='pynq_z2_tile_v1_53'
    O.mkdir(parents=True,exist_ok=True);assert not (O/'summary.json').exists()
    names=['rtl/product_tracker.v','sim/tb_tracker_invalid_baseline.sv','scripts/tracker_invalid_baseline.tcl','scripts/run_tracker_invalid_baseline.py','scripts/product_gate_no_wave.tcl']
    h={n:sha(R/n) for n in names};assert h['rtl/product_tracker.v']==sha(R.parent/'pynq_z2_tile_v1_41/rtl/product_tracker.v')
    result=dict(passed=False,negative_baseline_reproduced=False,source_sha256=h,hardware_used=False,
        scope='Production product_tracker RTL, injected invalid observation metadata; negative test success is not product acceptance')
    (O/'provenance.json').write_text(json.dumps(result,indent=2)+'\n');start=time.monotonic()
    try:
        cmd=['D:/2025.2/Vivado/bin/vivado.bat','-mode','batch','-source',str(R/'scripts/tracker_invalid_baseline.tcl'),'-log',str(O/'vivado.log'),'-journal',str(O/'vivado.jou'),'-notrace']
        with (O/'runner.log').open('w') as f:proc=subprocess.run(cmd,cwd=O,stdout=f,stderr=subprocess.STDOUT)
        assert proc.returncode==0
        log=(O/'simulate.log').read_text();assert 'PASS V142 NEGATIVE:' in log and 'Fatal:' not in log
        rows=list(csv.DictReader((O/'observations.csv').open()))
        assert len(rows)==5 and [int(r['product_id']) for r in rows]==[1,1,1,2,3]
        assert int(rows[2]['flags'],16)&4 and int(rows[3]['flags'],16)&2 and int(rows[4]['flags'],16)&2
        assert h=={n:sha(R/n) for n in names}
        result.update(passed=True,negative_baseline_reproduced=True,observations=rows,source_unchanged=True,
            proof_sha256={n:sha(O/n) for n in ('simulate.log','observations.csv','runner.log','provenance.json')})
    finally:
        result['run_seconds']=time.monotonic()-start;(O/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,negative_baseline_reproduced=True,observations=len(rows))))
if __name__=='__main__':main()
