"""Bounded experimental arithmetic RTL check; no detector/board claim."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,time

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);base=Path(__file__).resolve().parent
    sources=[base/'packed_pe.sv',base/'tb_packed_pe.sv'];started=time.monotonic()
    for name,args in [('xvlog',['-sv',*map(str,sources)]),('xelab',['tb_packed_pe','-s','test','-debug','typical']),('xsim',['test','-runall'])]:
        with (a.out/(name+'.log')).open('w') as log:
            subprocess.run(['D:/2025.2/Vivado/bin/'+name+'.bat',*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
    log=(a.out/'xsim.log').read_text(errors='replace')
    match=re.search(r'PACKED_PE_RTL_PASS checked=(\d+) stalled=(\d+) reset_flushes=(\d+)',log)
    if not match or 'Fatal:' in log or 'Error:' in log:raise RuntimeError('No clean arithmetic RTL pass')
    j=dict(scope='EXPERIMENTAL_ARITHMETIC_UNIT_RTL_NOT_DETECTOR_OR_BOARD',passed=True,
        checked=int(match[1]),stalled=int(match[2]),reset_flushes=int(match[3]),
        sources={str(s):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
        elapsed_seconds=time.monotonic()-started,integrated_into_detector=False)
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
if __name__=='__main__':main()
