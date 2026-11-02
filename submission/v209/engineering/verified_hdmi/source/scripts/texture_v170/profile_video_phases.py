"""Coarse non-invasive DDR phase observation during autonomous PL video.

Both ARM cores are halted. No HLS start/control reads or per-frame writes.
Host timestamps bracket debug reads, so these are interval-censored timing
estimates, not cycle-accurate measurements. The FPGA model is unchanged.
"""
from pathlib import Path
import argparse,hashlib,json,re,statistics,subprocess


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    for key in ['hardware','video','out']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--seconds',type=int,default=10);a=p.parse_args()
    if not 5<=a.seconds<=60:raise ValueError('Use 5-60 seconds')
    live=json.loads((a.video/'report.json').read_text())
    if not live['left_running'] or not live['both_arm_cores_halted']:raise ValueError('Validated running video required')
    for key in ['bit','xsa']:
        if sha(a.hardware/('system.'+key))!=live['programmed_build']['build'][key+'_sha256']:raise ValueError('Wrong build')
    a.out.mkdir(parents=True,exist_ok=False)
    script=r'''if {[catch {
connect -url tcp:127.0.0.1:3121
targets -set -filter {name == "APU"}
loadhw -hw @@XSA@@
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != @@BOOT@@} {error "Boot changed"}
proc halt_core {} {if {[catch {stop} why] && $why ne "Already stopped"} {error $why}}
targets -set -filter {name =~ "ARM*#0"};halt_core
targets -set -filter {name =~ "ARM*#1"};halt_core
puts "HALT_START_BEGIN";puts [targets];puts "HALT_START_END"
targets -set -filter {name == "APU"}
if {[expr [lindex [mrd -value 0x43c20000 1] 0]] != 1} {error "Video not enabled"}
set start [clock clicks -microseconds]
set end [expr {$start+@@DURATION@@}]
set midpoint [expr {$start+@@DURATION@@/2}]
set mid 0
while {[clock clicks -microseconds]<$end} {
 set before [clock clicks -microseconds]
 set phase [expr [lindex [mrd -value 0x07000020 1] 0]]
 set values [mrd -value 0x43c20004 2]
 set after [clock clicks -microseconds]
 puts "PHASE_SAMPLE $before $after $phase $values"
 if {!$mid && $after>=$midpoint} {puts "HALT_MID_BEGIN";puts [targets];puts "HALT_MID_END";set mid 1}
}
mwr 0x43c20000 0
set drained 0
for {set i 0} {$i<100} {incr i} {
 if {!([expr [lindex [mrd -value 0x43c20004 1] 0]]&1)} {set drained 1;break}
 after 100
}
if {!$drained} {error "Video did not drain"}
set final [mrd -value 0x43c20000 14]
if {[expr [lindex $final 6]]} {error "PL fault"}
puts "PHASE_FINAL $final"
puts "HALT_FINAL_BEGIN";puts [targets];puts "HALT_FINAL_END"
puts "NONINVASIVE_PHASE_OBSERVATION_COMPLETE"
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
'''
    script=script.replace('@@XSA@@','{'+(a.hardware/'system.xsa').as_posix()+'}').replace('@@BOOT@@',str(live['programmed_build']['boot_identity'])).replace('@@DURATION@@',str(a.seconds*1000000))
    (a.out/'observe.tcl').write_text(script)
    with (a.out/'observe.log').open('w') as log:
        r=subprocess.run(['D:/2025.2/Vitis/bin/xsdb.bat',str(a.out/'observe.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=a.seconds+90)
    log=(a.out/'observe.log').read_text()
    if r.returncode or 'NONINVASIVE_PHASE_OBSERVATION_COMPLETE' not in log:raise RuntimeError('Observation failed')
    for key in ['START','MID','FINAL']:
        state=re.search('HALT_'+key+'_BEGIN(.*?)HALT_'+key+'_END',log,re.S)
        if not state or len(re.findall(r'ARM Cortex-A9[^\r\n]*\((?:Stopped|Suspended)\)',state[1]))!=2:
            raise ValueError('ARM halt check failed')
    records=[]
    for text in re.findall(r'PHASE_SAMPLE ([^\r\n]+)',log):
        begin,end,phase,status,count=[int(v,0) for v in text.split()]
        if end<begin or not 0<=phase<=47 or status&16:raise ValueError('Invalid phase/status sample')
        records.append(dict(begin_us=begin,end_us=end,phase=phase,status=status,completed=count))
    groups={}
    for left,right in zip(records,records[1:]):
        delta=((right['begin_us']+right['end_us'])-(left['begin_us']+left['end_us']))/2
        if delta<=0:raise ValueError('Nonmonotonic timestamps')
        bucket='capture_or_wait' if left['status']&2 else ('post_cnn_head_and_mask' if left['phase']==47 else 'phase_'+str(left['phase']))
        frame=groups.setdefault(left['completed'],{})
        frame[bucket]=frame.get(bucket,0)+delta
    keys=list(groups)
    if len(keys)<5:raise ValueError('Insufficient complete frames')
    complete=[groups[k] for k in keys[1:-1]];all_buckets=sorted({b for f in complete for b in f})
    times={b:statistics.mean(f.get(b,0) for f in complete)/1000 for b in all_buckets}
    report=dict(scope='COARSE_HOST_POLLED_DDR_PHASE_TIMING_NOT_CYCLE_ACCURATE',
        source_video_report_sha256=sha(a.video/'report.json'),samples=len(records),complete_frame_intervals=len(complete),
        median_debug_read_span_us=statistics.median(r['end_us']-r['begin_us'] for r in records),
        mean_milliseconds_per_frame_by_observed_phase=times,
        interpretation='phase_0 includes input preprocessing and task 1; phase_k means task k completed, so task k+1 is running; phase_47 covers feature head, codebook search and mask. Capture/wait is separate.',
        both_arm_cores_halted=True,cpu_detection=False,gpu_detection=False,
        hls_control_reads=0,per_frame_start_writes=0,video_left_running=False)
    (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
