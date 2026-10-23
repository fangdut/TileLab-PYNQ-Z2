"""Small generated-RTL unit simulation; does not simulate the full detector."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess,time

def main():
    p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    base=Path(__file__).resolve().parent;root=base.parents[1]
    spec=importlib.util.spec_from_file_location('rowcheck',root/'tools/fpga_texture_v170/check_row_address.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);proof=mod.inspect(a.hls);assert proof['passed']
    a.out.mkdir(parents=True,exist_ok=False)
    sources=[a.hls/'solution/syn/verilog'/name for name in ['texture_integer_row_offset.v','texture_integer_mul_11ns_10ns_21_4_0.v']]+[base/'tb_row_address.sv']
    started=time.monotonic()
    for name,args in [('xvlog',['-sv',*map(str,sources)]),('xelab',['tb_row_address','-s','test','-debug','typical']),('xsim',['test','-runall'])]:
        with (a.out/(name+'.log')).open('w') as log:
            subprocess.run(['D:/2025.2/Vivado/bin/'+name+'.bat',*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    log=(a.out/'xsim.log').read_text(errors='replace')
    marker='ROW_ADDRESS_GENERATED_RTL_EXHAUSTIVE_AND_ENABLE_STALL_PASS checked=1048576'
    if marker not in log or 'Fatal:' in log or 'Error:' in log:raise RuntimeError('No clean generated row unit RTL PASS')
    j=dict(scope='GENERATED_ROW_UNIT_RTL_NOT_FULL_DETECTOR_TIMING_OR_BOARD',passed=True,
        exhaustive_legal_helper_inputs=1048576,elapsed_seconds=time.monotonic()-started,
        generated_structure=proof,sources={str(s):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
        diagnostic=[s for s in log.splitlines() if marker in s])
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
if __name__=='__main__':main()
