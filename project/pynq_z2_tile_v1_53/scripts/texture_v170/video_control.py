"""JTAG configure/observe PL video scheduling with BOTH ARM cores halted.

No per-frame start writes and no image arithmetic. Requires the same programmed
build to have passed the exposed 117-photo numerical regression first.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
from verify_video import verify

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    for name in ['hardware','program','validation','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--seconds',type=int,default=15);p.add_argument('--leave-running',action='store_true');a=p.parse_args()
    if not 5<=a.seconds<=60:raise ValueError('Use 5-60 seconds')
    if not verify(a.hardware)['video']:raise ValueError('Not a video hardware build')
    program=json.loads((a.program/'identity.json').read_text());summary=json.loads((a.validation/'summary.json').read_text())
    plan=json.loads((a.validation/'plan.json').read_text())
    if summary.get('scope')!='PHYSICAL_V170_FULL_INTEGER_PL' or summary['cases']!=117 or not summary['all_integer_outputs_exact']:
        raise ValueError('Physical regression incomplete')
    if plan['programmed_build']!=program:
        raise ValueError('Physical regression belongs to another programmed build/boot')
    if len(set(plan['selected_before_inference']))!=117:
        raise ValueError('Physical regression does not cover 117 unique photos')
    for name in ['bit','xsa']:
        if sha(a.hardware/('system.'+name))!=program['build'][name+'_sha256']:raise ValueError('Wrong programmed hardware')
    a.out.mkdir(parents=True,exist_ok=False)
    script=r'''if {[catch {
connect -url tcp:127.0.0.1:3121
targets -set -filter {name == "APU"}
loadhw -hw XSA
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != BOOT} {error "Unexpected boot identity"}
if {[expr [lindex [mrd -value 0x43c20030 1] 0]] != 0x17100001} {error "Wrong video register identity"}
if {[expr [lindex [mrd -value 0x05f0000c 1] 0]] != 0} {error "ARM transport still owns inference"}
targets -set -filter {name =~ "ARM*#0"}
stop
targets -set -filter {name =~ "ARM*#1"}
stop
puts "ARM_HALTED_BEGIN"
puts [targets]
puts "ARM_HALTED_END"
targets -set -filter {name == "APU"}
if {[expr [lindex [mrd -value 0x43c20004 1] 0]] & 1} {error "PL already owns input; refusing reconfiguration"}
set control [expr [lindex [mrd -value 0x43c10000 1] 0]]
if {!($control & 4)} {error "HLS is not idle"}
mwr 0x43c10000 0
foreach {offset address} {0x10 0x08000000 0x1c 0x10000000 0x28 0x06000000 0x34 0x07000000} {
 mwr [expr {0x43c10000+$offset}] $address
 mwr [expr {0x43c10004+$offset}] 0
}
mwr 0x43c10040 720
mwr 0x43c10048 720
mwr 0x43c20000 1
puts "PL_ENABLE_SINGLE_WRITE"
for {set i 0} {$i<SAMPLES} {incr i} {
 puts "VIDEO_SAMPLE [clock milliseconds] [mrd -value 0x43c20000 14]"
 after 250
}
STOP
puts "PL_VIDEO_OBSERVATION_FINISHED"
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
'''
    stop=r'''mwr 0x43c20000 0
set idle 0
for {set i 0} {$i<100} {incr i} {
 if {!([expr [lindex [mrd -value 0x43c20004 1] 0]] & 1)} {set idle 1;break}
 after 100
}
puts "VIDEO_FINAL [clock milliseconds] [mrd -value 0x43c20000 14]"
if {!$idle} {error "Capture/inference has not drained; input buffer remains PL-owned"}
'''
    script=script.replace('XSA','{'+(a.hardware/'system.xsa').resolve().as_posix()+'}').replace('BOOT',str(program['boot_identity'])).replace('SAMPLES',str(a.seconds*4)).replace('STOP','puts "PL_LEFT_RUNNING"' if a.leave_running else stop)
    (a.out/'control.tcl').write_text(script)
    with (a.out/'control.log').open('w') as log:
        run=subprocess.run(['D:/2025.2/Vitis/bin/xsdb.bat',str(a.out/'control.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=a.seconds+90)
    log=(a.out/'control.log').read_text();samples=[]
    for line in log.splitlines():
        if line.startswith(('VIDEO_SAMPLE ','VIDEO_FINAL ')):
            fields=line.split();values=[int(x,0) for x in fields[2:]]
            if len(values)!=14:raise ValueError('Unexpected register snapshot')
            samples.append(dict(timestamp_ms=int(fields[1]),registers=values))
    (a.out/'samples.json').write_text(json.dumps(samples,indent=2))
    halted=re.search(r'ARM_HALTED_BEGIN(.*?)ARM_HALTED_END',log,re.S)
    if not halted or len(re.findall(r'ARM Cortex-A9.*Stopped',halted[1]))!=2:raise RuntimeError('Both-core halt proof missing')
    if run.returncode or 'PL_VIDEO_OBSERVATION_FINISHED' not in log:raise RuntimeError('Video control failed; inspect control.log; CPUs remain halted')
    rows=[r for r in samples if r['registers'][2]>0]
    if len(rows)<2:raise RuntimeError('No autonomous HDMI detections observed')
    first,last=rows[0],rows[-1];frames=(last['registers'][2]-first['registers'][2])&0xffffffff
    seconds=(last['timestamp_ms']-first['timestamp_ms'])/1000
    capture_progress=(last['registers'][4]-first['registers'][4])&0xffffffff
    if frames<2 or not capture_progress or any(r['registers'][6] for r in samples):raise RuntimeError('Video progress/fault check failed')
    distinct_crc=len({r['registers'][5] for r in rows})
    report=dict(scope='PHYSICAL_AUTONOMOUS_HDMI_WITH_BOTH_ARM_CORES_HALTED',programmed_build=program,
        samples=len(rows),frames=frames,elapsed_wall_seconds=seconds,frame_rate=frames/seconds,
        distinct_capture_crc32=distinct_crc,dynamic_input_observed=distinct_crc>1,
        capture_frame_sequence_first=first['registers'][4],
        capture_frame_sequence_last=last['registers'][4],both_arm_cores_halted=True,pl_enable_writes=1,
        cpu_per_frame_start_writes=0,cpu_detection=False,gpu_detection=False,
        precision_scope='Engineering video throughput only; compare image decisions separately',
        physical_regression_plan_sha256=sha(a.validation/'plan.json'),
        physical_regression_summary_sha256=sha(a.validation/'summary.json'),left_running=a.leave_running)
    (a.out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

if __name__=='__main__':main()
