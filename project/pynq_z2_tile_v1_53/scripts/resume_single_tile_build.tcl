# Resume finished IPs and retry failed IP synthesis serially. No board access.
set root [file normalize [file join [file dirname [info script]] ..]]
set_param general.maxThreads 2
if {![file exists $root/SINGLE_TILE_BUILD_ONLY]} {error "Isolated build marker missing"}
set out $root/reports/v164/hardware_run03
if {[file exists $out]} {error "Do not overwrite evidence"}
file mkdir $out
open_project $root/pynq_z2_tile_v1_53.xpr
set log [open $out/resumed_runs.txt w]
foreach r [get_runs -filter {IS_SYNTHESIS == 1}] {
 set status [get_property STATUS $r]
 puts $log "$r : $status"
 if {[string match -nocase {*error*} $status] || [string match -nocase {*failed*} $status]} {reset_run $r}
}
close $log
reset_run synth_1
launch_runs synth_1 -jobs 1
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Synthesis failed"}
launch_runs impl_1 -to_step write_bitstream -jobs 1
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {error "Implementation failed"}
open_run impl_1
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
report_timing_summary -file $out/before_timing.rpt
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
