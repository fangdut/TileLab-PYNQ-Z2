"""Read a paused physical HDMI frame/result over JTAG; image files are display only."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,zlib
import numpy as np
from PIL import Image

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    for n in ['hardware','video','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();report=json.loads((a.video/'report.json').read_text())
    if report['left_running'] or not report['both_arm_cores_halted']:raise ValueError('Pause/drain video with both ARM cores halted first')
    for name in ['bit','xsa']:
        if sha(a.hardware/('system.'+name))!=report['programmed_build']['build'][name+'_sha256']:raise ValueError('Hardware changed')
    a.out.mkdir(parents=True,exist_ok=False)
    def path(p):return '{'+p.resolve().as_posix()+'}'
    script=r'''if {[catch {
connect -url tcp:127.0.0.1:3121
targets -set -filter {name == "APU"}
loadhw -hw XSA
proc halt_core {} {if {[catch {stop} why] && $why ne "Already stopped"} {error $why}}
targets -set -filter {name =~ "ARM*#0"}
halt_core
targets -set -filter {name =~ "ARM*#1"}
halt_core
puts "ARM_STATE_BEGIN"
puts [targets]
puts "ARM_STATE_END"
targets -set -filter {name == "APU"}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != BOOT} {error "Boot changed"}
set video_version [expr [lindex [mrd -value 0x43c20030 1] 0]]
if {$video_version != EXPECTED_VERSION} {error "Video version changed"}
if {$video_version == 0x17200001} {
 set color_before [mrd -value 0x43c20038 4]
 puts "SNAPSHOT_COLOR $color_before"
}
set before [mrd -value 0x43c20000 14]
if {[expr [lindex $before 0]] || ([expr [lindex $before 1]] & 1)} {error "PL still owns input"}
if {!([expr [lindex $before 1]] & 8) || ([expr [lindex $before 1]] & 16) || [expr [lindex $before 6]] || ![expr [lindex $before 2]]} {error "No valid fault-free published result"}
puts "SNAPSHOT_REGISTERS $before"
mrd -bin -file RGB 0x06000000 518400
mrd -bin -file RESULT 0x07000000 519200
if {[mrd -value 0x43c20000 14] ne $before} {error "Video registers changed during snapshot"}
if {$video_version == 0x17200001 && [mrd -value 0x43c20038 4] ne $color_before} {error "Color registers changed during snapshot"}
puts "ARM_FINAL_BEGIN"
puts [targets]
puts "ARM_FINAL_END"
puts "PAUSED_PHYSICAL_FRAME_DUMP_PASSED"
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
'''
    version=report.get('video_register_version',0x17100001)
    script=script.replace('EXPECTED_VERSION',str(version)).replace('XSA',path(a.hardware/'system.xsa')).replace('BOOT',str(report['programmed_build']['boot_identity'])).replace('RGB',path(a.out/'rgb.bin')).replace('RESULT',path(a.out/'raw_result.bin'))
    (a.out/'snapshot.tcl').write_text(script)
    with (a.out/'snapshot.log').open('w') as log:
        run=subprocess.run(['D:/2025.2/Vitis/bin/xsdb.bat',str(a.out/'snapshot.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=180)
    log=(a.out/'snapshot.log').read_text();state=re.search(r'ARM_STATE_BEGIN(.*?)ARM_STATE_END',log,re.S)
    if run.returncode or 'PAUSED_PHYSICAL_FRAME_DUMP_PASSED' not in log:raise RuntimeError('Snapshot failed')
    if not state or len(re.findall(r'ARM Cortex-A9[^\r\n]*\((?:Stopped|Suspended)\)',state[1]))!=2:raise RuntimeError('ARM cores were not both halted')
    final=re.search(r'ARM_FINAL_BEGIN(.*?)ARM_FINAL_END',log,re.S)
    if not final or len(re.findall(r'ARM Cortex-A9[^\r\n]*\((?:Stopped|Suspended)\)',final[1]))!=2:raise RuntimeError('ARM cores did not remain halted during dump')
    values=[int(x,0) for x in re.search(r'SNAPSHOT_REGISTERS (.*)',log)[1].split()]
    color_match=re.search(r'SNAPSHOT_COLOR ([^\r\n]+)',log)
    color_words=[int(x,0) for x in color_match[1].split()] if color_match else None
    if version==0x17200001 and color_words!=report['color_registers']:
        raise ValueError('Snapshot color configuration differs from observed video')
    raw=(a.out/'rgb.bin').read_bytes();rgb_crc=zlib.crc32(raw)
    if len(raw)!=720*720*4 or rgb_crc!=values[5]:raise ValueError('Captured DDR frame differs from PL capture CRC')
    words=np.frombuffer(raw,dtype='<u4').reshape(720,720)
    rgb=np.stack(((words>>16)&255,(words>>8)&255,words&255),axis=-1).astype('u1')
    result=np.fromfile(a.out/'raw_result.bin',dtype='<u4');header=result[:16]
    if len(result)!=519200 or header[0]!=0x17000001 or header[1] or header[5]!=28 or header[7]!=720*720 or header[8]!=47:raise ValueError('Invalid physical result header')
    if header[9]!=values[10] or header[3]!=values[7] or header[4]!=values[8] or header[6]!=values[9] or bool(header[2])!=bool(values[1]&4):raise ValueError('Result/PL latch mismatch')
    mask=result[800:].reshape(720,720)
    if np.any(mask>1) or int(mask.sum())!=int(header[6]):raise ValueError('Invalid physical mask')
    Image.fromarray(rgb).save(a.out/'actual_hdmi_input.png')
    Image.fromarray((mask*255).astype('u1')).save(a.out/'actual_pl_mask.png')
    overlay=rgb.copy();selected=mask.astype(bool)
    overlay[selected]=(rgb[selected].astype('u2')*3//5+np.array([102,0,0],dtype='u2')).clip(0,255).astype('u1')
    Image.fromarray(overlay).save(a.out/'actual_pl_overlay.png')
    evidence=dict(scope='PAUSED_PHYSICAL_HDMI_INPUT_AND_PL_RESULT',video_report_sha256=sha(a.video/'report.json'),
        rgb_crc32=rgb_crc,capture_sequence=values[4],pl_sequence=int(header[9]),pl_image_alarm=int(header[2]),
        arm_cores_halted_during_dump=True,
        input_scope='Captured PL RGB after startup black/gain calibration, before detector resize',
        video_register_version=version,color_registers=color_words,
        color_startup_profile=report.get('color_startup_profile'),
        pl_peak=int(header[3]),pl_threshold=int(header[4]),pl_mask_pixels=int(header[6]),
        source_photo_id=None,source_photo_binding='Not inferred from the current player status; inspect/match the captured frame separately',
        cpu_detection=False,gpu_detection=False,files={n:sha(a.out/n) for n in ['rgb.bin','raw_result.bin','actual_hdmi_input.png','actual_pl_mask.png','actual_pl_overlay.png']})
    (a.out/'evidence.json').write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence),flush=True)

if __name__=='__main__':main()
