"""Compare pipelined result validation with the accepted historical RTL."""
from pathlib import Path
import argparse, hashlib, json, subprocess, time

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    base=Path(__file__).resolve().parent;a.out.mkdir(parents=True,exist_ok=False)
    sources=[base/'rtl/pl_result_latch.sv',base/'sim/pl_result_latch_reference_v176.sv',base/'sim/tb_result_latch.sv']
    historical=sources[1].read_bytes().replace(b'module pl_result_latch_reference_v176 #(',b'module pl_result_latch #(')
    if hashlib.sha256(historical).hexdigest()!='18d804d6540e5b03217733f42b057236b15933339c6a99e5dfdae506f311f13f':
        raise ValueError('Historical oracle differs from accepted RTL')
    started=time.monotonic()
    for name,args in [('xvlog',['-sv',*map(str,sources)]),('xelab',['tb_result_latch','-s','test','-debug','typical']),('xsim',['test','-runall'])]:
        with (a.out/(name+'.log')).open('w') as log:
            subprocess.run(['D:/2025.2/Vivado/bin/'+name+'.bat',*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    log=(a.out/'xsim.log').read_text(errors='replace')
    if 'RESULT_LATCH_HISTORICAL_EQUIVALENCE_STALL_ERROR_SEQUENCE_WRAP_RESET_PASS transactions=6190' not in log or 'Fatal:' in log or 'Error:' in log:
        raise RuntimeError('No clean historical result-latch equivalence PASS')
    summary=dict(scope='HISTORICAL_RESULT_VALIDATION_EQUIVALENCE_RTL_NOT_TIMING_OR_BOARD',passed=True,transactions=6190,
        extra_validation_cycles=2,elapsed_seconds=time.monotonic()-started,
        sources={str(s.relative_to(base)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources})
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
