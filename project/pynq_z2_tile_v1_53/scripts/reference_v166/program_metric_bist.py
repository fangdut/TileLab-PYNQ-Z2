"""Temporarily program the arithmetic BIST after timing/source checks.

No HDMI/ethernet application runs in this image. Restore transport afterward.
Hardware results must be independently read with read_metric_bist.tcl.
"""
from pathlib import Path
import argparse,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from deployment_single_tile import sha,verify
from program_single_tile import ensure_workstation_stopped

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--build',type=Path,required=True);ap.add_argument('--vectors',type=Path,required=True);ap.add_argument('--xsdb',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();build=a.build.resolve();a.out.mkdir(parents=True,exist_ok=False)
    status=dict(line.split('=',1) for line in (build/'implementation_status.txt').read_text().splitlines() if '=' in line)
    if float(status['setup_slack_ns'])<0 or float(status['hold_slack_ns'])<0 or int(status['drc_errors']):raise ValueError('BIST timing/DRC failed; do not program')
    ensure_workstation_stopped()
    bundle=ROOT/'releases/v164';verify(bundle);vectors=json.loads((a.vectors/'manifest.json').read_text())
    sources={'rtl_sha256':ROOT/'experimental/reference_v166/rtl/reference_metric_v166.v','testbench_sha256':ROOT/'sim/tb_reference_metric_v166.sv'}
    if any(sha(p)!=vectors[k] for k,p in sources.items()):raise ValueError('Source does not match simulated vectors')
    for name in ('board_input.mem','board_expected.mem'):
        if sha(a.vectors/name)!=vectors['sha256'][name]:raise ValueError('Board ROM changed')
    bit=build/'metric_bist.runs/impl_1/bist_wrapper.bit';ltx=build/'metric_bist.ltx'
    proof=dict(scope='HARDWARE_WINDOW_METRIC_ONLY_NOT_VIDEO_NOT_REFERENCE_DDR_NOT_REAL_ACCURACY',programmed=False,accuracy_qualified=False,reference_video_integrated=False,bit_sha256=sha(bit),ltx_sha256=sha(ltx),rtl_sha256=sha(sources['rtl_sha256']),bist_sha256=sha(ROOT/'experimental/reference_v166/rtl/reference_metric_bist_v166.v'),vectors=vectors,implementation_status=status)
    (a.out/'preflight.json').write_text(json.dumps(proof,indent=2)+'\n')
    script=a.out/'program.tcl'
    lines=['if {[catch {','connect','targets -set -filter {name =~ "ARM*#0"}','rst -system','after 1000','stop','fpga -file {'+bit.as_posix()+'}','source {'+(bundle/'ps7_init.tcl').as_posix()+'}','ps7_init','ps7_post_config','after 200','targets -set -filter {name == "APU"}','set fc [expr [lindex [mrd -value 0xF8000170 1] 0]]','set pll [expr [lindex [mrd -value 0xF8000108 1] 0]]','puts [format "METRIC_BIST_FCLK0 0x%08x IOPLL 0x%08x" $fc $pll]','if {($fc&0x03f03f30)!=0x00200500 || ($pll&0x0007f000)!=0x00014000} {error "Expected board100MHz clock configuration"}','disconnect','puts "METRIC_BIST_PROGRAMMED"','} why]} {puts stderr "METRIC_BIST_PROGRAM_FAILED: $why";exit 1}','exit 0']
    script.write_text('\n'.join(lines)+'\n')
    with (a.out/'program.log').open('w',encoding='utf8') as log:subprocess.run([str(a.xsdb),str(script)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    transcript=(a.out/'program.log').read_text(encoding='utf8',errors='replace')
    if transcript.splitlines().count('METRIC_BIST_PROGRAMMED')!=1 or 'METRIC_BIST_PROGRAM_FAILED:' in transcript:raise RuntimeError('Metric BIST programming failed')
    proof['programmed']=True;(a.out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))

if __name__=='__main__':main()
