if {[catch {
connect -url tcp:127.0.0.1:3121
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v172_hw02/system.xsa}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != 142768567} {error "Boot changed"}
proc halt_core {} {if {[catch {stop} why] && $why ne "Already stopped"} {error $why}}
targets -set -filter {name =~ "ARM*#0"};halt_core
targets -set -filter {name =~ "ARM*#1"};halt_core
puts "HALT_START_BEGIN";puts [targets];puts "HALT_START_END"
targets -set -filter {name == "APU"}
if {[expr [lindex [mrd -value 0x43c20000 1] 0]] != 1} {error "Video not enabled"}
set start [clock clicks -microseconds]
set end [expr {$start+10000000}]
set midpoint [expr {$start+10000000/2}]
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
