"""PL control/slot integration with independent stalled AXI/capture/HLS models."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);base=Path(__file__).resolve().parent
    sources=[base/'rtl/frame_slot_queue.sv',base/'rtl/pl_frame_scheduler_overlap.sv',base/'sim/tb_overlap_scheduler.sv']
    started=time.monotonic()
    for name,args in [('xvlog',['-sv',*map(str,sources)]),('xelab',['tb_overlap_scheduler','-s','test','-debug','typical']),('xsim',['test','-runall'])]:
        with (a.out/(name+'.log')).open('w') as log:
            subprocess.run(['D:/2025.2/Vivado/bin/'+name+'.bat',*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    text=(a.out/'xsim.log').read_text(errors='replace')
    if 'OVERLAP_SCHEDULER_POINTER_AXI_STALL_DRAIN_IDENTITY_FAULTS_PASS' not in text or 'Fatal:' in text or 'Error:' in text:
        raise RuntimeError('Scheduler integration did not pass')
    j=dict(scope='SLOT_AND_CONTROL_AXI_MODEL_RTL_NOT_REAL_DDR_HDMI_CNN_OR_BOARD',passed=True,
        elapsed_seconds=time.monotonic()-started,sources={str(s.relative_to(base)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources})
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j),flush=True)
if __name__=='__main__':main()
