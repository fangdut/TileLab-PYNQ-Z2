if {[catch {
connect -url tcp:127.0.0.1:3121
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v171_hw03/system.xsa}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != 410811972} {error "Unexpected boot identity"}
if {[expr [lindex [mrd -value 0x43c20030 1] 0]] != 0x17100001} {error "Wrong video register identity"}
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

puts "ARM_FINAL_BEGIN"
puts [targets]
puts "ARM_FINAL_END"
puts "PL_VIDEO_OBSERVATION_FINISHED"
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
