set root [file normalize [file join [file dirname [info script]] ..]]
cd $root
open_project $root/pynq_z2_tile_v1_53.xpr
# Vivado may leave a module-reference OOC checkpoint marked current after an
# internal child RTL file changes. Compare source mtimes explicitly so a top-only
# rebuild cannot silently reuse the stale custom video checkpoint.
set custom_changed 0
foreach {run sources} {
 system_bypass_0_synth_1 {axis_gray.v raster_delay.v sobel3x3.v gaussian3x3.v video_stats.v window3x3.v video_core.v directional_valley.v config_bridge.v candidate_stats.v brightness_stats.v raster_morph.v region_grid.v video_bypass.v}
 system_regions_regs_0_synth_1 {region_axi.v}
 system_capture_0_synth_1 {frame_capture_sg.v product_tracker.v}
 system_status_0_synth_1 {status_cdc.v}
} {
 set dcp [file join [get_property DIRECTORY [get_runs $run]] [string map {_synth_1 .dcp} $run]]
 set dirty [expr {![file exists $dcp]}]
 foreach src $sources {
  if {!$dirty && [file mtime $root/rtl/$src]>[file mtime $dcp]} {set dirty 1}
 }
 if {$dirty} {puts "Refreshing custom RTL checkpoint: $run";reset_run $run;set custom_changed 1}
}
if {$custom_changed} {reset_run synth_1}
foreach r [get_runs] {
 if {[regexp -nocase {error|fail} [get_property STATUS $r]]} {reset_run $r}
}
if {[get_property PROGRESS [get_runs synth_1]] ne "100%" || [get_property NEEDS_REFRESH [get_runs synth_1]]} {
 reset_run synth_1
 launch_runs synth_1 -jobs 1
 wait_on_run synth_1
}
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Synthesis failed"}
if {[get_property PROGRESS [get_runs impl_1]] ne "100%" || [get_property NEEDS_REFRESH [get_runs impl_1]]} {
 reset_run impl_1
 launch_runs impl_1 -to_step write_bitstream -jobs 2
 wait_on_run impl_1
}
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {error "Implementation failed"}
open_run impl_1
report_timing_summary -file $root/reports/timing_summary.rpt
if {[get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]<0 || [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]<0} {error "Timing failed; hardware export is blocked"}
report_utilization -file $root/reports/utilization.rpt
report_drc -file $root/reports/drc.rpt
report_cdc -file $root/reports/cdc.rpt
file mkdir $root/pynq_z2_tile_v1_53.sdk
report_cdc -details -file $root/reports/cdc_details.rpt
report_methodology -file $root/reports/methodology.rpt
report_bus_skew -file $root/reports/bus_skew.rpt
write_debug_probes -force $root/pynq_z2_tile_v1_53.sdk/system.ltx
write_hw_platform -fixed -include_bit -force -file $root/pynq_z2_tile_v1_53.sdk/system.xsa
file copy -force $root/pynq_z2_tile_v1_53.runs/impl_1/system_wrapper.bit $root/pynq_z2_tile_v1_53.sdk/system.bit
close_project
