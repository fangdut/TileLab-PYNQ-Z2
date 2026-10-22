connect -url tcp:127.0.0.1:3121
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v173_hw04/system.xsa}
foreach address {0xe000b000 0xe000b004 0xe000b008 0xe000b010 0xe000b014 0xe000b018 0xe000b01c 0xe000b020} {
 if {[catch {mrd -value $address 1} value]} {puts "GEM $address UNAVAILABLE $value"} else {puts "GEM $address $value"}
}
targets -set -filter {name =~ "ARM*#0"}
if {[catch {con} why]} {puts $why}
targets -set -filter {name =~ "ARM*#1"}
if {[catch {con} why]} {puts $why}
puts "RESUMED_DIAGNOSTIC_NO_START_WRITES"
puts [targets]
disconnect
exit
