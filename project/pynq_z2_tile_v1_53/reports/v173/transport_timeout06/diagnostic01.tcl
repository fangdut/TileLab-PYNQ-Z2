connect -url tcp:127.0.0.1:3121
puts "BEFORE_HALT_TARGETS"
puts [targets]
targets -set -filter {name =~ "ARM*#0"}
if {[catch {stop} why] && $why ne "Already stopped"} {error $why}
puts "ARM0_PC"
rrd pc
targets -set -filter {name =~ "ARM*#1"}
if {[catch {stop} why] && $why ne "Already stopped"} {error $why}
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v173_hw04/system.xsa}
puts "TRANSPORT_STATUS"
puts [mrd -value 0x05f00000 8]
puts "PL_RESULT_HEADER"
puts [mrd -value 0x07000000 16]
puts "HLS_CONTROL_AFTER_ARM_HALT_DIAGNOSTIC_ONLY"
puts [mrd -value 0x43c10000 1]
puts "VIDEO_CONTROL"
puts [mrd -value 0x43c20000 14]
puts [targets]
disconnect
exit
