if {[catch {
connect -url tcp:127.0.0.1:3121
proc halt_core {} {if {[catch {stop} why] && $why ne "Already stopped"} {error $why}}
targets -set -filter {name =~ "ARM*#0"}
halt_core
targets -set -filter {name =~ "ARM*#1"}
halt_core
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.xsa}
puts "CURRENT_BOOT_MAILBOX [mrd -value 0x05f00000 8]"
puts "CURRENT_PL_ID [mrd -value 0x41200000 1]"
puts "TARGETS_FINAL"
puts [targets]
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
