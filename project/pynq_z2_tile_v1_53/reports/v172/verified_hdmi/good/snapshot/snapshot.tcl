if {[catch {
connect -url tcp:127.0.0.1:3121
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v172_hw02/system.xsa}
proc halt_core {} {if {[catch {stop} why] && $why ne "Already stopped"} {error $why}}
targets -set -filter {name =~ "ARM*#0"}
halt_core
targets -set -filter {name =~ "ARM*#1"}
halt_core
puts "ARM_STATE_BEGIN"
puts [targets]
puts "ARM_STATE_END"
targets -set -filter {name == "APU"}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != 142768567} {error "Boot changed"}
set video_version [expr [lindex [mrd -value 0x43c20030 1] 0]]
if {$video_version != 387973121} {error "Video version changed"}
if {$video_version == 0x17200001} {
 set color_before [mrd -value 0x43c20038 4]
 puts "SNAPSHOT_COLOR $color_before"
}
set before [mrd -value 0x43c20000 14]
if {[expr [lindex $before 0]] || ([expr [lindex $before 1]] & 1)} {error "PL still owns input"}
if {!([expr [lindex $before 1]] & 8) || ([expr [lindex $before 1]] & 16) || [expr [lindex $before 6]] || ![expr [lindex $before 2]]} {error "No valid fault-free published result"}
puts "SNAPSHOT_REGISTERS $before"
mrd -bin -file {D:/Vivado/TileLab_RealPhotos_20261020/v172_acceptance02/good_snapshot/rgb.bin} 0x06000000 518400
mrd -bin -file {D:/Vivado/TileLab_RealPhotos_20261020/v172_acceptance02/good_snapshot/raw_result.bin} 0x07000000 519200
if {[mrd -value 0x43c20000 14] ne $before} {error "Video registers changed during snapshot"}
if {$video_version == 0x17200001 && [mrd -value 0x43c20038 4] ne $color_before} {error "Color registers changed during snapshot"}
puts "ARM_FINAL_BEGIN"
puts [targets]
puts "ARM_FINAL_END"
puts "PAUSED_PHYSICAL_FRAME_DUMP_PASSED"
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
