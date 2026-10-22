"""Reject a synthetic20-cycle RAW hazard despite an allocated32-slot RAM."""
from pathlib import Path
import argparse,hashlib,json,sys
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'tools/fpga_texture_v170'))
from check_mac_recurrence import inspect
def main():
    p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    safe=inspect(a.hls);assert safe['slots']==32 and safe['minimum_reuse_iterations']==16 and safe['all_banks_safe']
    assert all(r['read_stage']==23 and r['write_stage']==32 for r in safe['banks'])
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'src').mkdir();(a.out/'solution/syn/verilog').mkdir(parents=True)
    source=a.hls/'src/texture_integer.cpp';(a.out/'src/texture_integer.cpp').write_bytes(source.read_bytes())
    files=[f for f in (a.hls/'solution/syn/verilog').glob('*mac_row_Pipeline*.v') if 'acc_ce0_local' in f.read_text()]
    assert len(files)==1;rtl=files[0];text=rtl.read_text()
    assert 'ap_enable_reg_pp0_iter23' in text
    text=text.replace('ap_enable_reg_pp0_iter23','ap_enable_reg_pp0_iter12')
    (a.out/'solution/syn/verilog'/rtl.name).write_text(text)
    unsafe=inspect(a.out)
    assert not unsafe['all_banks_safe'] and all(r['write_minus_read']==20 for r in unsafe['banks'])
    assert all(r['write_minus_read']<unsafe['slots'] for r in unsafe['banks'])
    j=dict(scope='STATIC_GUARD_NEGATIVE_FIXTURE_NOT_COMPILABLE_RTL_OR_SIMULATION',passed=True,
        actual_safe_delta=9,allocated_ram_slots=32,logical_DW_reuse=16,
        synthetic_delta20_rejected_despite_fitting_allocated32=True,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        actual_rtl_sha256=hashlib.sha256(rtl.read_bytes()).hexdigest())
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
if __name__=='__main__':main()
