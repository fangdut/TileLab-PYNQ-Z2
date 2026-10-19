# Resume successful OOC checkpoints; retry failed tool startup serially.
set root [file normalize [file join [file dirname [info script]] ..]]
if {![file exists $root/CANDIDATE_BUILD_ONLY]} {error "Isolated build marker required"}
cd $root
set_param general.maxThreads 2
open_project $root/pynq_z2_tile_v1_53.xpr
foreach r [get_runs] {
 set state [get_property STATUS $r]
 puts "RUN_STATE $r $state"
 if {[string match -nocase *error* $state]} {reset_run $r}
}
reset_run synth_1
launch_runs synth_1 -jobs 1
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Synthesis failed"}
launch_runs impl_1 -to_step write_bitstream -jobs 1
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {error "Implementation failed"}
open_run impl_1
set out $root/reports/v155/hardware_run03
if {[file exists $out]} {error "Never overwrite evidence"}
file mkdir $out
foreach {cmd name} {report_timing_summary timing_summary report_utilization utilization report_drc drc report_cdc cdc report_bus_skew bus_skew report_methodology methodology} {$cmd -file $out/$name.rpt}
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
set errors [llength [get_drc_violations -quiet -filter {SEVERITY == Error}]]
set fp [open $out/implementation_status.txt w]
puts $fp "setup_slack_ns=$setup"
puts $fp "hold_slack_ns=$hold"
puts $fp "drc_errors=$errors"
close $fp
if {$setup<0 || $hold<0 || $errors>0} {error "Timing/DRC failed; export blocked"}
write_debug_probes -force $out/system.ltx
write_hw_platform -fixed -include_bit -force -file $out/system.xsa
file copy $root/pynq_z2_tile_v1_53.runs/impl_1/system_wrapper.bit $out/system.bit
close_project

