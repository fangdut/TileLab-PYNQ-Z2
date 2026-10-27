"""Read-only coarse last-frame PL-stage timing; does not halt either ARM."""
from pathlib import Path
import argparse,json,hashlib,struct,subprocess
def main():
    p=argparse.ArgumentParser();p.add_argument('--result',type=Path,required=True);p.add_argument('--hardware',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--xsdb',default='D:/2025.2/Vitis/bin/xsdb.bat');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    r=json.loads(a.result.read_text());boot=r['boot_identity'];dump=(a.out/'trace.bin').resolve().as_posix();xsa=(a.hardware/'system.xsa').resolve().as_posix()
    script='''if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 1000000
targets -set -filter {name == "APU"}
loadhw -hw {XSA_PATH}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != BOOT_ID} {error "Changed boot"}
if {[expr [lindex [mrd -value 0x43c20000 1] 0]] != 0 || ([expr [lindex [mrd -value 0x43c20004 1] 0]] & 1)} {error "Video must be idle"}
mrd -bin -file {DUMP_PATH} 0x05f01000 200
puts "READONLY_TRACE_PASS"
disconnect
} why]} {puts stderr $why;exit 1}
exit 0
'''
    script=script.replace('XSA_PATH',xsa).replace('BOOT_ID',str(boot)).replace('DUMP_PATH',dump);tcl=a.out/'read_trace.tcl';tcl.write_text(script)
    with (a.out/'read_trace.log').open('w') as log:subprocess.run([a.xsdb,str(tcl)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=40)
    ticks=struct.unpack('<100Q',(a.out/'trace.bin').read_bytes());assert ticks[99]==r['ps_global_timer_ticks'] and ticks[47] and ticks[97]
    hz=r['ps_timer_hz'];timing=json.loads((a.hardware/'implementation_status.json').read_text())
    summary=dict(scope='READONLY_LAST_FRAME_COARSE_PL_TIMING_NOT_AXI_BANDWIDTH_OR_VIDEO_FPS',boot_identity=boot,frame_sequence=r['pl_frame_sequence'],sampling_seconds=0.0001,cnn_through_task47_seconds=ticks[47]/hz,projection_nearest_to_first_score_seconds=(ticks[97]-ticks[47])/hz,score_to_completion_seconds=(ticks[99]-ticks[97])/hz,total_engine_seconds=ticks[99]/hz,physical=timing,trace_sha256=hashlib.sha256((a.out/'trace.bin').read_bytes()).hexdigest(),decision='KEEP_VERIFIED100MHZ_CORE_NO_UNPROVEN_CLOCK_OR_PARALLELISM_CHANGE',reason='Only0.013ns setup margin and218of220 DSP already used; stage sampling does not by itself establish a safe new RTL optimization')
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
