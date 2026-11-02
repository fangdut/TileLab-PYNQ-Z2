"""Dynamic DDR writer and complete video stream/control integration fixtures."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--case',choices=['writer','pipeline','video_regs','hpd'],required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);base=Path(__file__).resolve().parent
    names=['hdmi_hpd_startup.v'] if a.case=='hpd' else ['video_regs.v'] if a.case=='video_regs' else ['roi_ddr_writer.sv'] if a.case=='writer' else ['video_color_correct.sv','video_roi_tokens.sv','video_capture_link.sv','roi_ddr_writer.sv','frame_slot_queue.sv','pl_frame_scheduler_overlap.sv','pl_result_latch.sv','hdmi_detector_pipeline.v']
    sources=[base/'rtl'/name for name in names]+[base/'sim'/('tb_'+a.case+'.sv')]
    started=time.monotonic()
    commands=[('xvlog',['-sv',*map(str,sources),'D:/2025.2/Vivado/data/verilog/src/glbl.v']),
        ('xelab',['tb_'+a.case,'glbl','-L','xpm','-L','unisims_ver','-s','test','-debug','typical']),('xsim',['test','-runall'])]
    for name,args in commands:
        with (a.out/(name+'.log')).open('w') as log:
            subprocess.run(['D:/2025.2/Vivado/bin/'+name+'.bat',*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    text=(a.out/'xsim.log').read_text(errors='replace')
    if '_PASS' not in text or 'Fatal:' in text or 'Error:' in text:raise RuntimeError('No clean integration PASS; inspect logs')
    j=dict(scope='DYNAMIC_DDR_AND_VIDEO_CONTROL_BUS_MODEL_RTL_NOT_REAL_HDMI_CNN_OR_BOARD',test=a.case,passed=True,
        elapsed_seconds=time.monotonic()-started,sources={str(s.relative_to(base)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources})
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j),flush=True)
if __name__=='__main__':main()
