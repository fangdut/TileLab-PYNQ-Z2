# Fresh isolated build only; never program hardware.
set root [file normalize [file join [file dirname [info script]] ..]]
if {![file exists $root/CANDIDATE_BUILD_ONLY]} {error "Isolated build marker required"}
if {[file exists $root/reports/v155/hardware_run01]} {error "Never overwrite implementation evidence"}
if {[catch {source $root/scripts/create_project.tcl} why options]} {
 if {[string match {Timing failed;*} $why] && [file exists $root/pynq_z2_tile_v1_53.runs/impl_1/system_wrapper_routed.dcp]} {
  close_project
  source $root/scripts/close_support_timing_v155.tcl
  exit
 }
 return -options $options $why
}
open_project $root/pynq_z2_tile_v1_53.xpr
open_run impl_1
set out $root/reports/v155/hardware_run01
file mkdir $out
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
set errors [llength [get_drc_violations -quiet -filter {SEVERITY == Error}]]
set fp [open $out/implementation_status.txt w]
puts $fp "setup_slack_ns=$setup"
puts $fp "hold_slack_ns=$hold"
puts $fp "drc_errors=$errors"
close $fp
if {$setup<0 || $hold<0 || $errors>0} {error "Candidate export blocked by timing/DRC"}
foreach name {timing_summary utilization drc cdc cdc_details methodology bus_skew} {
 file copy $root/reports/$name.rpt $out/$name.rpt
}
foreach name {system.bit system.xsa system.ltx} {
 file copy $root/pynq_z2_tile_v1_53.sdk/$name $out/$name
}
close_project
