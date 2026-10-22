set out {D:/Vivado/TileLab_RealPhotos_20261020/v173_hw03}
set video 1
set jobs 1
set opt_directive Default
set_param general.maxThreads 4
open_project $out/texture_v170.xpr
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Completed synthesis required"}
reset_run impl_1
set_property STEPS.OPT_DESIGN.ARGS.DIRECTIVE $opt_directive [get_runs impl_1]
set_property STEPS.ROUTE_DESIGN.TCL.PRE $out/physical_scripts/replicate_controls.tcl [get_runs impl_1]
launch_runs impl_1 -to_step write_bitstream -jobs $jobs
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {error "Implementation failed"}
open_run impl_1
report_timing_summary -file $out/timing_summary.rpt
report_clocks -file $out/clocks.rpt
report_utilization -file $out/utilization.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
report_drc -file $out/drc.rpt
set errors [llength [get_drc_violations -filter {SEVERITY == Error}]]
set f [open $out/implementation_status.json w]
puts $f "{\"setup_slack_ns\":$setup,\"hold_slack_ns\":$hold,\"drc_errors\":$errors,\"pl_clock_mhz\":100}"
close $f
if {$setup<0 || $hold<0 || $errors} {error "Timing/DRC failed"}
if {$video} {
 report_cdc -details -file $out/video_cdc.rpt
 report_bus_skew -file $out/bus_skew.rpt
 report_exceptions -file $out/video_exceptions.rpt
 set f [open $out/bus_skew.rpt r];set proof [read $f];close $f
 if {[regexp -nocase {VIOLATED} $proof]} {error "Asynchronous FIFO bus skew failed"}
 if {[regexp -all {Slack\s+\(MET\)} $proof]<2 || ![string match *rd_pntr_cdc_inst/src_gray_ff_reg* $proof] || ![string match *wr_pntr_cdc_inst/src_gray_ff_reg* $proof]} {error "Both FIFO Gray-bus skew constraints must be present and pass"}
 write_checkpoint -force $out/video_accepted.dcp
}
write_hw_platform -fixed -include_bit -force -file $out/system.xsa
# Preserve the XSA export's canonical sibling BIT. A second write_bitstream
# may change only DATE/TIME, which still breaks our required whole-file SHA.
if {![file exists $out/system.bit]} {
 file copy $out/texture_v170.runs/impl_1/system_wrapper.bit $out/system.bit
}
puts "TEXTURE_V170_IMPLEMENTATION_PASSED"
exit
