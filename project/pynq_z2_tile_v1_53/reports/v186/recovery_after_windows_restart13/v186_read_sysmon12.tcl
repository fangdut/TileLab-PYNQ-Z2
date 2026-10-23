if {[catch {
open_hw_manager
connect_hw_server -url localhost:3121
set cable [lindex [get_hw_targets] 0]
if {$cable eq ""} {error "No hardware target"}
current_hw_target $cable
set_property PARAM.FREQUENCY 1000000 $cable
open_hw_target
set device [lindex [get_hw_devices -filter {PART =~ "xc7z020*"}] 0]
if {$device eq ""} {error "Expected xc7z020 device"}
current_hw_device $device
refresh_hw_device -update_hw_probes false $device
set mon [lindex [get_hw_sysmons -of_objects $device] 0]
if {$mon eq ""} {error "No readable XADC"}
report_property -all $mon
for {set sample 0} {$sample < 6} {incr sample} {
 refresh_hw_sysmon $mon
 set values [list sample $sample]
 foreach p {TEMPERATURE VCCINT VCCAUX VCCBRAM VCCPINT VCCPAUX VCCO_DDR MIN_VCCINT MAX_VCCINT MIN_VCCPINT MAX_VCCPINT MIN_VCCO_DDR MAX_VCCO_DDR} {
  lappend values $p [get_property $p $mon]
 }
 puts "SYSMON_READONLY $values"
 after 1000
}
close_hw_target
disconnect_hw_server
close_hw_manager
} why opts]} {puts stderr $why;exit 1}
exit 0
