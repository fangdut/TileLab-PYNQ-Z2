"""Controlled original-photo HDMI experiment; PL detects, PC only selects input.

Requires an already running, validated PL video session. Both ARM cores are
halted for this experiment. Three fresh completions and stable input/result
checks separate photo transitions from each recorded decision.
"""
from pathlib import Path
import argparse, hashlib, json, re, subprocess
from verify_video import verify


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    for key in ['hardware','video','catalog','source-status','source-command','out']:
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--limit',type=int,default=117)
    a=p.parse_args()
    live=json.loads((a.video/'report.json').read_text())
    if not live['left_running'] or not live['both_arm_cores_halted'] or not verify(a.hardware)['video']:
        raise ValueError('Requires a validated enabled autonomous video session')
    for key in ['bit','xsa']:
        if sha(a.hardware/('system.'+key))!=live['programmed_build']['build'][key+'_sha256']:
            raise ValueError('Wrong physical hardware')
    photos=json.loads(a.catalog.read_text())[:a.limit]
    if not 1<=len(photos)<=117 or len({r['id'] for r in photos})!=len(photos):
        raise ValueError('Expected unique original-photo catalog')
    for photo in photos:
        if not re.fullmatch('[a-f0-9]{24}',photo['id']) or not photo['original_unedited'] or sha(Path(photo['file']))!=photo['sha256']:
            raise ValueError('Original source provenance failed')
    a.out.mkdir(parents=True,exist_ok=False)
    plan=dict(scope='CONTROLLED_ORIGINAL_PHOTO_HDMI_DEVELOPMENT_EXPERIMENT',
        photos=photos,video_report_sha256=sha(a.video/'report.json'),
        benchmark_is_blind=False,threshold_adaptation=False,model_adaptation=False,
        cpu_detection=False,gpu_detection=False,
        source_binding='Owned HDMI input player SHA/status plus settled stable PL completions; selected photos require separate DDR snapshot inspection/audit')
    (a.out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    def tp(path):return '{'+path.resolve().as_posix()+'}'
    template=r'''if {[catch {
connect -url tcp:127.0.0.1:3121
targets -set -filter {name == "APU"}
loadhw -hw @@XSA@@
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != @@BOOT@@} {error "Boot identity changed"}
proc halt_core {} {if {[catch {stop} why] && $why ne "Already stopped"} {error $why}}
targets -set -filter {name =~ "ARM*#0"}
halt_core
targets -set -filter {name =~ "ARM*#1"}
halt_core
proc halt_proof {marker} {puts "HALT_${marker}_BEGIN";puts [targets];puts "HALT_${marker}_END"}
halt_proof START
targets -set -filter {name == "APU"}
if {[expr [lindex [mrd -value 0x43c20000 1] 0]] != 1} {error "PL video is not enabled"}
if {[expr [lindex [mrd -value 0x43c20030 1] 0]] != @@VERSION@@} {error "Video version changed"}
set version @@VERSION@@
if {$version == 0x17200001} {
 set color_before [mrd -value 0x43c20038 4]
 @@COLOR_EXPECT@@
}
set items {@@ITEMS@@}
set source_status @@STATUS@@
set source_command @@COMMAND@@
set output @@OUTPUT@@
proc current_source {id hash} {
 global source_status
 set readable 0
 for {set attempt 0} {$attempt<10} {incr attempt} {
  if {![catch {set f [open $source_status r]}]} {
   set data [read $f];close $f;set readable 1;break
  }
  after 20
 }
 if {!$readable} {error "Source status unavailable"}
 foreach token [list "\"image_id\":\"$id\"" "\"original_sha256\":\"$hash\"" {"physical_window_bounds_verified":true} {"running":true} {"paused":true} {"calibration_pattern":false}] {
  if {[string first $token $data]<0} {return ""}
 }
 return $data
}
foreach {id hash} $items {
 set f [open $source_command w];puts $f "photo:$id";close $f
 set source ""
 for {set i 0} {$i<40} {incr i} {
  after 100
  if {![catch {set source [current_source $id $hash]}] && $source ne ""} {break}
 }
 if {$source eq ""} {error "Source player did not acknowledge original $id"}
 after 650
 set before [mrd -value 0x43c20000 14]
 set base [expr [lindex $before 2]]
 set fresh 0
 for {set i 0} {$i<40} {incr i} {
  after 100
  set values [mrd -value 0x43c20000 14]
  if {[expr [lindex $values 6]]} {error "PL fault during $id"}
  if {(([expr [lindex $values 2]]-$base)&0xffffffff)>=3} {set fresh 1;break}
 }
 if {!$fresh} {error "No three fresh detections for $id"}
 for {set sample 0} {$sample<3} {incr sample} {
  if {[current_source $id $hash] eq ""} {error "Input changed during $id"}
  set values [mrd -value 0x43c20000 14]
  puts "PHOTO_RESULT $id [clock milliseconds] $values"
  after 250
 }
 set source [current_source $id $hash]
 if {$source eq ""} {error "Input changed after $id"}
 set f [open "$output/${id}_source.json" w];puts $f $source;close $f
 halt_proof $id
}
mwr 0x43c20000 0
set drained 0
for {set i 0} {$i<100} {incr i} {
 if {!([expr [lindex [mrd -value 0x43c20004 1] 0]] & 1)} {set drained 1;break}
 after 100
}
if {!$drained} {error "Final input buffer did not drain"}
if {$version==0x17200001 && [mrd -value 0x43c20038 4] ne $color_before} {error "Color profile changed"}
halt_proof FINAL
puts "HDMI_PHOTO_SERIES_COMPLETE"
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
'''
    color=live.get('color_registers')
    expected='\n'.join('if {[expr [lindex $color_before '+str(i)+']] != '+str(word)+'} {error "Color profile mismatch"}' for i,word in enumerate(color or []))
    replacements=dict(XSA=tp(a.hardware/'system.xsa'),BOOT=str(live['programmed_build']['boot_identity']),
        VERSION=str(live.get('video_register_version',0x17100001)),ITEMS=' '.join(r['id']+' '+r['sha256'] for r in photos),
        STATUS=tp(a.source_status),COMMAND=tp(a.source_command),OUTPUT=tp(a.out),COLOR_EXPECT=expected)
    for key,value in replacements.items():template=template.replace('@@'+key+'@@',value)
    (a.out/'experiment.tcl').write_text(template)
    with (a.out/'experiment.log').open('w') as log:
        run=subprocess.run(['D:/2025.2/Vitis/bin/xsdb.bat',str(a.out/'experiment.tcl')],
            stdout=log,stderr=subprocess.STDOUT,timeout=90+len(photos)*12)
    log=(a.out/'experiment.log').read_text()
    if run.returncode or 'HDMI_PHOTO_SERIES_COMPLETE' not in log:
        raise RuntimeError('HDMI experiment failed; inspect log; no accuracy result accepted')
    states=re.findall(r'HALT_\w+_BEGIN(.*?)HALT_\w+_END',log,re.S)
    if len(states)!=len(photos)+2 or any(len(re.findall(r'ARM Cortex-A9[^\r\n]*\((?:Stopped|Suspended)\)',s))!=2 for s in states):
        raise ValueError('ARM halt proof incomplete')
    observations={r['id']:[] for r in photos}
    for ident,stamp,data in re.findall(r'PHOTO_RESULT (\w+) (\d+) ([^\r\n]+)',log):
        words=[int(v,0) for v in data.split()]
        if len(words)!=14:raise ValueError('Bad register sample')
        observations[ident].append(dict(timestamp_ms=int(stamp),registers=words))
    results=[]
    for photo in photos:
        rows=observations[photo['id']]
        if len(rows)!=3:raise ValueError('Missing samples')
        regs=[r['registers'] for r in rows]
        stable=all(len({r[k] for r in regs})==1 for k in [5,7,8,9])
        if not stable or any(r[6] or not(r[1]&8) or r[1]&16 for r in regs):
            raise ValueError('Unstable/faulted physical result for '+photo['id'])
        if ((regs[-1][2]-regs[0][2])&0xffffffff) < 1:
            raise ValueError('No fresh detection during observation')
        alarm=bool(regs[-1][1]&4)
        if alarm!=(regs[-1][7]>regs[-1][8]):raise ValueError('Inconsistent PL decision')
        results.append(dict(id=photo['id'],label=photo['label'],alarm=alarm,
            correct=alarm==(photo['label']!='good'),peak=regs[-1][7],threshold=regs[-1][8],
            mask_pixels=regs[-1][9],captured_crc32=regs[-1][5],samples=rows,
            source_status_sha256=sha(a.out/(photo['id']+'_source.json'))))
    (a.out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    normal=[r for r in results if r['label']=='good'];anomaly=[r for r in results if r['label']!='good']
    first=results[0]['samples'][0];last=results[-1]['samples'][-1]
    duration=(last['timestamp_ms']-first['timestamp_ms'])/1000
    frames=(last['registers'][2]-first['registers'][2])&0xffffffff
    if duration<=0 or frames<1:raise ValueError('Invalid continuous progress interval')
    summary=dict(scope='PHYSICAL_CONTROLLED_ORIGINAL_PHOTO_HDMI_SERIES',cases=len(results),
        correct=sum(r['correct'] for r in results),normal_images=len(normal),
        normal_false_alarms=sum(r['alarm'] for r in normal),anomalies=len(anomaly),
        anomalies_detected=sum(r['alarm'] for r in anomaly),
        cracks=sum(r['label']=='crack' for r in results),cracks_detected=sum(r['alarm'] for r in results if r['label']=='crack'),
        both_arm_cores_halted=True,arm_halt_checks=len(states),cpu_per_frame_start_writes=0,
        cpu_detection=False,gpu_detection=False,benchmark_is_blind=False,threshold_adaptation=False,
        continuous_observation_seconds=duration,autonomous_frames_in_interval=frames,
        autonomous_hdmi_fps_over_photo_series=frames/duration,
        distinct_observed_photo_crcs=len({r['captured_crc32'] for r in results}),
        plan_sha256=sha(a.out/'plan.json'),results_sha256=sha(a.out/'results.json'),
        limitations=plan['source_binding'],left_running=False)
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
