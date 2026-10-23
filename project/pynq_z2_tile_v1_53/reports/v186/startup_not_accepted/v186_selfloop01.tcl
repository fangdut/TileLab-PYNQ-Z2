if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 3000000
puts [targets]
targets -set -filter {name =~ "ARM*#0"}
if {[catch {stop} why] && $why ne "Already stopped"} {error $why}
source {D:/Vivado/TileLab_RealPhotos_20261020/v179_acceptance01/program/ps7_init.tcl}
ps7_init
mwr 0x00100000 0xeafffffe
rwr pc 0x00100000
puts "LOOP_BEFORE_PC [rrd pc]"
stp
puts "LOOP_AFTER_STEP_PC [rrd pc]"
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.xsa}
puts "REASON_BEFORE_CLEAR [mrd -value 0xf8000258 1]"
mwr 0xf8000008 0xdf0d
set prior [expr [lindex [mrd -value 0xf8000258 1] 0]]
mwr 0xf8000258 [expr {$prior & 0xff80ffff}]
puts "REASON_CLEARED [mrd -value 0xf8000258 1]"
mwr 0xf8000004 0x767b
targets -set -filter {name =~ "ARM*#0"}
con
after 100
if {[catch {stop} why] && $why ne "Already stopped"} {error $why}
puts "LOOP_AFTER_RUN_PC [rrd pc]"
targets -set -filter {name == "APU"}
puts "REASON_AFTER_RUN [mrd -value 0xf8000258 1]"
puts "CLOCK_AFTER_RUN [mrd -value 0xf8000170 1]"
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
