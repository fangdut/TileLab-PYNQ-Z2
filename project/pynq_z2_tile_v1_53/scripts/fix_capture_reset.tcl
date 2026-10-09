set root [file normalize [file join [file dirname [info script]] ..]]
open_project $root/pynq_z2_tile_v1_5.xpr
open_bd_design [get_files system.bd]
update_ip_catalog -update_module_ref
update_module_reference -verbose [get_ips system_bypass_0]
set_property CONFIG.C_AUX_RESET_HIGH {1} [get_bd_cells capture_ready_reset]
validate_bd_design
if {[get_property CONFIG.C_EXT_RESET_HIGH [get_bd_cells capture_ready_reset]]!=1 || [get_property CONFIG.C_AUX_RESET_HIGH [get_bd_cells capture_ready_reset]]!=1} {error "Capture FIFO reset polarity incorrect"}
save_bd_design
generate_target all [get_files system.bd]
write_bd_tcl -force $root/scripts/system_generated.tcl
reset_run synth_1
launch_runs synth_1 -jobs 2
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Synthesis failed"}
launch_runs impl_1 -to_step write_bitstream -jobs 2
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {error "Implementation failed"}
open_run impl_1
report_timing_summary -file $root/reports/timing_summary.rpt
report_utilization -file $root/reports/utilization.rpt
report_drc -file $root/reports/drc.rpt
report_cdc -file $root/reports/cdc.rpt
report_cdc -details -file $root/reports/cdc_details.rpt
report_methodology -file $root/reports/methodology.rpt
report_bus_skew -file $root/reports/bus_skew.rpt
if {[get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]<0} {error "Setup timing failed"}
if {[get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]<0} {error "Hold timing failed"}
write_debug_probes -force $root/pynq_z2_tile_v1_5.sdk/system.ltx
write_hw_platform -fixed -include_bit -force -file $root/pynq_z2_tile_v1_5.sdk/system.xsa
file copy -force $root/pynq_z2_tile_v1_5.runs/impl_1/system_wrapper.bit $root/pynq_z2_tile_v1_5.sdk/system.bit
close_project
