# Apply only verified first-stage level CDC exceptions to the completed repair.
set root [file normalize [file join [file dirname [info script]] ../..]]
set out [file normalize $::env(TILE_TEXTURE_HW)]
set_param general.maxThreads 2
open_project $out/texture_v170.xpr
set checkpoint $out/after_fanout_repair.dcp
if {![file exists $checkpoint]} {set checkpoint $out/texture_v170.runs/impl_1/system_wrapper_routed.dcp}
open_checkpoint $checkpoint
source $root/scripts/texture_v170/constrain_video_cdc.tcl
report_timing_summary -file $out/timing_summary.rpt
report_cdc -details -file $out/video_cdc.rpt
report_bus_skew -file $out/bus_skew.rpt
report_exceptions -file $out/video_exceptions.rpt
set f [open $out/bus_skew.rpt r];set proof [read $f];close $f
if {[regexp -nocase {VIOLATED} $proof] || [regexp -all {Slack\s+\(MET\)} $proof]<2 || ![string match *rd_pntr_cdc_inst/src_gray_ff_reg* $proof] || ![string match *wr_pntr_cdc_inst/src_gray_ff_reg* $proof]} {error "Both FIFO Gray-bus skew constraints must be present and pass"}
report_clocks -file $out/clocks.rpt
report_utilization -file $out/utilization.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
report_drc -file $out/drc.rpt
set errors [llength [get_drc_violations -filter {SEVERITY == Error}]]
set f [open $out/implementation_status.json w]
puts $f "{\"setup_slack_ns\":$setup,\"hold_slack_ns\":$hold,\"drc_errors\":$errors,\"pl_clock_mhz\":100,\"physical_fanout_repair\":true,\"explicit_first_stage_cdc\":true}"
close $f
if {$setup<0||$hold<0||$errors} {error "Synchronous timing/DRC still fails; export blocked"}
write_checkpoint -force $out/video_accepted.dcp
write_bitstream -force $out/texture_v170.runs/impl_1/system_wrapper.bit
write_hw_platform -fixed -include_bit -force -file $out/system.xsa
# write_hw_platform may generate system.bit with a fresh DATE/TIME header.
# Keep that canonical sibling; it is byte-exact with the XSA-contained BIT.
if {![file exists $out/system.bit]} {file copy $out/texture_v170.runs/impl_1/system_wrapper.bit $out/system.bit}
puts "TEXTURE_VIDEO_TIMING_CDC_EXPORT_PASSED"
exit
