# Re-optimize the same placed/routed logical detector, refusing failed timing.
set root [file normalize [file join [file dirname [info script]] ../..]]
set out [file normalize $::env(TILE_TEXTURE_HW)]
set_param general.maxThreads 2
open_project $out/texture_v170.xpr
open_run impl_1
close_design
# This Vivado release accepts forced replication only before routing.
# Reuse the existing placed checkpoint; no C/HLS or synthesis changes.
open_checkpoint $out/texture_v170.runs/impl_1/system_wrapper_physopt.dcp
source $root/scripts/texture_v170/constrain_video_cdc.tcl
write_checkpoint -force $out/before_fanout_repair.dcp
source $root/scripts/texture_v170/replicate_controls.tcl
phys_opt_design -directive AggressiveFanoutOpt
route_design -directive Explore
report_timing_summary -file $out/timing_summary.rpt
report_utilization -file $out/utilization.rpt
report_clocks -file $out/clocks.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
report_drc -file $out/drc.rpt
set errors [llength [get_drc_violations -filter {SEVERITY == Error}]]
set f [open $out/implementation_status.json w]
puts $f "{\"setup_slack_ns\":$setup,\"hold_slack_ns\":$hold,\"drc_errors\":$errors,\"pl_clock_mhz\":100,\"physical_fanout_repair\":true}"
close $f
write_checkpoint -force $out/after_fanout_repair.dcp
if {$setup<0||$hold<0||$errors} {error "Physical replication still fails timing/DRC; export blocked"}
write_bitstream -force $out/texture_v170.runs/impl_1/system_wrapper.bit
write_hw_platform -fixed -include_bit -force -file $out/system.xsa
if {![file exists $out/system.bit]} {file copy $out/texture_v170.runs/impl_1/system_wrapper.bit $out/system.bit}
puts "TEXTURE_V170_PHYSICAL_REPAIR_PASSED"
exit
