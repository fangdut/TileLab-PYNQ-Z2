"""Isolated slot-owner RTL test. No HDMI/CNN/AXI integration or board claims."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);base=Path(__file__).resolve().parent
    sources=[base/'rtl/frame_slot_queue.sv',base/'sim/tb_frame_slot_queue.sv']
    started=time.monotonic()
    for tool,args in [('xvlog',['-sv',*map(str,sources)]),
                      ('xelab',['tb_frame_slot_queue','-s','slot_test','-debug','typical']),
                      ('xsim',['slot_test','-runall'])]:
        with (a.out/(tool+'.log')).open('w') as log:
            subprocess.run(['D:/2025.2/Vivado/bin/'+tool+'.bat',*args],cwd=a.out,
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    log=(a.out/'xsim.log').read_text(errors='replace')
    if 'FRAME_SLOT_QUEUE_RANDOM_DRAIN_IDENTITY_PASS' not in log or 'Fatal:' in log or 'Error:' in log:
        raise RuntimeError('No clean randomized ownership PASS; inspect log')
    j=dict(scope='ISOLATED_SLOT_OWNERSHIP_RTL_NOT_HDMI_AXI_CNN_OR_BOARD',passed=True,
        elapsed_seconds=time.monotonic()-started,
        sources={str(s.relative_to(base)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources})
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j),flush=True)

if __name__=='__main__':main()
