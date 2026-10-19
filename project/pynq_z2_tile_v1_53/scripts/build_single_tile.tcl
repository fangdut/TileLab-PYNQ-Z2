# Isolated implementation, no JTAG or hardware programming.
set root [file normalize [file join [file dirname [info script]] ..]]
if {![file exists $root/SINGLE_TILE_BUILD_ONLY]} {error "Use prepare_single_tile_build.py first"}
set out $root/reports/v164/hardware_run01
if {[file exists $out]} {error "Never overwrite build evidence"}
file mkdir $out
set ::env(TILE_NO_ILA) 1
if {[catch {source $root/scripts/create_project.tcl} why options]} {
 if {[string match {Timing failed;*} $why] && [file exists $root/pynq_z2_tile_v1_53.runs/impl_1/system_wrapper_routed.dcp]} {close_project} else {return -options $options $why}
}
open_project $root/pynq_z2_tile_v1_53.xpr
open_run impl_1
report_timing_summary -file $out/before_timing.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
if {$setup<0 || $hold<0} {phys_opt_design -directive AggressiveExplore}
report_timing_summary -file $out/timing_summary.rpt
report_utilization -file $out/utilization.rpt
report_drc -file $out/drc.rpt
report_cdc -details -file $out/cdc.rpt
report_bus_skew -file $out/bus_skew.rpt
report_methodology -file $out/methodology.rpt
report_route_status -file $out/route_status.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
set errors [llength [get_drc_violations -quiet -filter {SEVERITY == Error}]]
set f [open $out/implementation_status.txt w]
puts $f "setup_slack_ns=$setup";puts $f "hold_slack_ns=$hold";puts $f "drc_errors=$errors";close $f
write_checkpoint $out/system_timing_closed.dcp
if {$setup<0 || $hold<0 || $errors>0} {error "Timing/DRC failed; deployment export blocked"}
write_bitstream $out/system.bit
close_project
set run $root/pynq_z2_tile_v1_53.runs/impl_1
file copy -force $out/system.bit $run/system_wrapper.bit
file copy -force $out/system_timing_closed.dcp $run/system_wrapper_routed.dcp
open_project $root/pynq_z2_tile_v1_53.xpr
open_run impl_1
write_hw_platform -fixed -include_bit -force -file $out/system.xsa
close_project
