# Isolated hardware arithmetic experiment. No application/HDMI acceptance.
set root [file normalize [file join [file dirname [info script]] .. ..]]
set_param general.maxThreads 2
foreach name {TILE_METRIC_BIST_OUT TILE_REF_VECTORS} {if {![info exists ::env($name)]} {error "Set $name"}}
set out [file normalize $::env(TILE_METRIC_BIST_OUT)]
if {[file exists $out]} {error "Choose a new output directory"}
create_project metric_bist $out -part xc7z020clg400-1
add_files [list $root/experimental/reference_v166/rtl/reference_metric_v166.v $root/experimental/reference_v166/rtl/reference_metric_bist_v166.v $::env(TILE_REF_VECTORS)/board_input.mem $::env(TILE_REF_VECTORS)/board_expected.mem]
create_bd_design bist
set ps7 [create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 ps7]
source $root/scripts/ps7_preset.tcl
set_property -dict [list CONFIG.PCW_USE_M_AXI_GP0 {0} CONFIG.PCW_USE_S_AXI_HP0 {0} CONFIG.PCW_EN_CLK0_PORT {1} CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} CONFIG.PCW_EN_CLK1_PORT {0} CONFIG.PCW_EN_CLK2_PORT {0} CONFIG.PCW_EN_CLK3_PORT {0}] $ps7
make_bd_intf_pins_external [get_bd_intf_pins ps7/DDR]
make_bd_intf_pins_external [get_bd_intf_pins ps7/FIXED_IO]
set_property name DDR [get_bd_intf_ports DDR_0]
set_property name FIXED_IO [get_bd_intf_ports FIXED_IO_0]
create_bd_cell -type module -reference reference_metric_bist_v166 selftest
create_bd_cell -type ip -vlnv xilinx.com:ip:vio:3.0 monitor
set_property -dict [list CONFIG.C_NUM_PROBE_IN {1} CONFIG.C_PROBE_IN0_WIDTH {64} CONFIG.C_NUM_PROBE_OUT {1} CONFIG.C_PROBE_OUT0_WIDTH {1} CONFIG.C_PROBE_OUT0_INIT_VAL {0x0}] [get_bd_cells monitor]
connect_bd_net [get_bd_pins ps7/FCLK_CLK0] [get_bd_pins selftest/clk] [get_bd_pins monitor/clk]
connect_bd_net [get_bd_pins ps7/FCLK_RESET0_N] [get_bd_pins selftest/resetn]
connect_bd_net [get_bd_pins selftest/status] [get_bd_pins monitor/probe_in0]
connect_bd_net [get_bd_pins monitor/probe_out0] [get_bd_pins selftest/restart]
validate_bd_design;save_bd_design
generate_target all [get_files bist.bd]
make_wrapper -files [get_files bist.bd] -top
add_files $out/metric_bist.gen/sources_1/bd/bist/hdl/bist_wrapper.v
set_property top bist_wrapper [current_fileset]
launch_runs synth_1 -jobs 2;wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Synthesis failed"}
launch_runs impl_1 -to_step write_bitstream -jobs 2;wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {error "Implementation failed"}
open_run impl_1
report_timing_summary -file $out/timing_summary.rpt
report_drc -file $out/drc.rpt
report_utilization -file $out/utilization.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
set errors [llength [get_drc_violations -quiet -filter {SEVERITY == Error}]]
set f [open $out/implementation_status.txt w];puts $f "setup_slack_ns=$setup";puts $f "hold_slack_ns=$hold";puts $f "drc_errors=$errors";close $f
if {$setup<0||$hold<0||$errors>0} {error "Timing/DRC failed; do not program"}
write_debug_probes $out/metric_bist.ltx
close_project
