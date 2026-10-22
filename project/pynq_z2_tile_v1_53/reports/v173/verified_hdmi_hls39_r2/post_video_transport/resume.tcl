connect -url tcp:127.0.0.1:3121
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v173_hw04/system.xsa}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != 1678502908} {error "Wrong boot"}
if {[expr [lindex [mrd -value 0x43c20000 1] 0]] != 0} {error "Video still enabled"}
if {[expr [lindex [mrd -value 0x43c20004 1] 0]] & 1} {error "Video not drained"}
targets -set -filter {name =~ "ARM*#0"}
if {[catch {con} why]} {puts $why}
targets -set -filter {name =~ "ARM*#1"}
if {[catch {con} why]} {puts $why}
puts "AFTER_VIDEO_TRANSPORT_RESUMED_NO_PL_START_WRITES"
puts [targets]
disconnect
exit