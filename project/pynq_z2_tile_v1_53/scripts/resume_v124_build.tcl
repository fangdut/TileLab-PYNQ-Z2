# Resume completed OOC jobs after an isolated Vivado process crash.
# Source RTL, IP settings and timing requirements are unchanged.
set root [file normalize [file join [file dirname [info script]] ..]]
open_project $root/pynq_z2_tile_v1_53.xpr
set_param general.maxThreads 2
foreach r [get_runs *_synth_1] {
 set status [get_property STATUS $r]
 puts "Resume audit: $r : $status"
 if {[string match {*ERROR*} $status] || [string match {*Error*} $status] || [string match {*Failed*} $status]} {
  reset_run $r
  launch_runs $r -jobs 1
  wait_on_run $r
  if {[get_property PROGRESS $r] ne "100%"} {error "OOC retry failed: $r"}
 }
}
reset_run synth_1
launch_runs synth_1 -jobs 1
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Synthesis failed"}
launch_runs impl_1 -to_step write_bitstream -jobs 1
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {error "Implementation failed"}
open_run impl_1
report_timing_summary -file $root/reports/timing_summary.rpt
if {[get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]<0 || [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]<0} {error "Timing failed; hardware export blocked"}
report_utilization -file $root/reports/utilization.rpt
report_drc -file $root/reports/drc.rpt
report_cdc -file $root/reports/cdc.rpt
report_cdc -details -file $root/reports/cdc_details.rpt
report_methodology -file $root/reports/methodology.rpt
report_bus_skew -file $root/reports/bus_skew.rpt
write_debug_probes -force $root/pynq_z2_tile_v1_53.sdk/system.ltx
write_hw_platform -fixed -include_bit -force -file $root/pynq_z2_tile_v1_53.sdk/system.xsa
file copy -force $root/pynq_z2_tile_v1_53.runs/impl_1/system_wrapper.bit $root/pynq_z2_tile_v1_53.sdk/system.bit
close_project
