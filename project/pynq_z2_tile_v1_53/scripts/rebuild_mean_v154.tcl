# Incremental rebuild in a marked, isolated build copy. No board programming.
set root [file normalize [file join [file dirname [info script]] ..]]
if {![file exists $root/CANDIDATE_BUILD_ONLY]} {error "Use an isolated candidate build directory with CANDIDATE_BUILD_ONLY"}
set run_id [lindex $argv 0]
if {$run_id eq ""} {set run_id run01}
if {![regexp {^[a-z0-9_-]+$} $run_id]} {error "Invalid run ID"}
set out $root/reports/v154/hardware_mean_$run_id
if {[file exists $out]} {error "Never overwrite an implementation result"}
file mkdir $out
set_param general.maxThreads 2
open_project $root/pynq_z2_tile_v1_53.xpr
set_property ip_repo_paths [list $root/ip_repo] [current_project]
update_ip_catalog
add_files -norecurse [list $root/rtl/directional_mean_valley.v $root/rtl/mean_dual_scale_valley.v]
update_compile_order -fileset sources_1
open_bd_design [get_files system.bd]
# video_bypass has the same external ports. Refresh its dependency graph;
# changing a module-reference interface is unnecessary for this body-only edit.
validate_bd_design
save_bd_design
generate_target all [get_files system.bd] -force
reset_run system_bypass_0_synth_1
reset_run synth_1
launch_runs synth_1 -jobs 1
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Synthesis failed"}
launch_runs impl_1 -to_step write_bitstream -jobs 1
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {error "Implementation failed"}
open_run impl_1
report_timing_summary -file $out/timing_summary.rpt
report_utilization -file $out/utilization.rpt
report_drc -file $out/drc.rpt
report_cdc -details -file $out/cdc.rpt
report_bus_skew -file $out/bus_skew.rpt
report_methodology -file $out/methodology.rpt
set setup_slack [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold_slack [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
set fp [open $out/implementation_status.txt w]
puts $fp "setup_slack_ns=$setup_slack"
puts $fp "hold_slack_ns=$hold_slack"
close $fp
if {$setup_slack<0 || $hold_slack<0} {error "Candidate timing failed; export blocked"}
if {[llength [get_drc_violations -quiet -filter {SEVERITY == Error}]]} {error "DRC error; export blocked"}
write_debug_probes -force $out/system.ltx
write_hw_platform -fixed -include_bit -force -file $out/system.xsa
file copy -force $root/pynq_z2_tile_v1_53.runs/impl_1/system_wrapper.bit $out/system.bit
close_project
