if {[catch {
connect -url tcp:127.0.0.1:3121
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v173_hw04/system.xsa}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != 1678502908} {error "Unexpected boot identity"}
set video_version [expr [lindex [mrd -value 0x43c20030 1] 0]]
if {$video_version != 0x17100001 && $video_version != 0x17200001} {error "Wrong video register identity"}
puts "VIDEO_VERSION $video_version"
if {[expr [lindex [mrd -value 0x05f0000c 1] 0]] != 0} {error "ARM transport still owns inference"}
proc halt_core {} {
 if {[catch {stop} why] && $why ne "Already stopped"} {error $why}
}
targets -set -filter {name =~ "ARM*#0"}
halt_core
targets -set -filter {name =~ "ARM*#1"}
halt_core
puts "ARM_HALTED_BEGIN"
puts [targets]
puts "ARM_HALTED_END"
targets -set -filter {name == "APU"}
if {[expr [lindex [mrd -value 0x43c20004 1] 0]] & 1} {error "PL already owns input; refusing reconfiguration"}
if {[expr [lindex [mrd -value 0x43c20000 1] 0]] != 0} {error "Disable/drain capture before reconfiguration"}
if {$video_version != 0x17200001} {error "Color profile requires V172 PL hardware"}
mwr 0x43c20038 260
mwr 0x43c2003c 314
mwr 0x43c20040 403
if {$video_version == 0x17200001} {
 set ready 0
 for {set i 0} {$i<100} {incr i} {
  if {[expr [lindex [mrd -value 0x43c20044 1] 0]] == 1} {set ready 1;break}
  after 20
 }
 if {!$ready} {error "Color coefficients not acknowledged by HDMI pixel clock"}
 set color_before [mrd -value 0x43c20038 4]
 if {[expr [lindex $color_before 0]] != 260} {error "Unexpected PL color coefficient"}
if {[expr [lindex $color_before 1]] != 314} {error "Unexpected PL color coefficient"}
if {[expr [lindex $color_before 2]] != 403} {error "Unexpected PL color coefficient"}
 puts "VIDEO_COLOR_CONFIG $color_before"
}
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
for {set i 0} {$i<20} {incr i} {
 puts "VIDEO_SAMPLE [clock milliseconds] [mrd -value 0x43c20000 14]"
 if {$i==20/2} {puts "ARM_MID_BEGIN";puts [targets];puts "ARM_MID_END"}
 after 250
}
mwr 0x43c20000 0
set idle 0
for {set i 0} {$i<100} {incr i} {
 if {!([expr [lindex [mrd -value 0x43c20004 1] 0]] & 1)} {set idle 1;break}
 after 100
}
puts "VIDEO_FINAL [clock milliseconds] [mrd -value 0x43c20000 14]"
if {!$idle} {error "Capture/inference has not drained; input buffer remains PL-owned"}

if {$video_version == 0x17200001 && [mrd -value 0x43c20038 4] ne $color_before} {error "Color configuration changed during detection"}
puts "ARM_FINAL_BEGIN"
puts [targets]
puts "ARM_FINAL_END"
puts "PL_VIDEO_OBSERVATION_FINISHED"
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
