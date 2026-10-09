set root [file normalize [file join [file dirname [info script]] ..]]
set_param general.maxThreads 2
cd $root
if {[file exists $root/pynq_z2_tile_v1_53.xpr] && ![info exists ::env(TILE_RECREATE)]} {error "Project exists; open the XPR or use rebuild.tcl"}
# Vivado -force removes matching .sdk directories. Preserve the software seed.
set sdk $root/pynq_z2_tile_v1_53.sdk
set seed $root/sdk_seed
if {[file exists $seed]} {error "sdk_seed already exists; inspect it before creating project"}
if {[file exists $sdk]} {file rename $sdk $seed}
try {
 create_project pynq_z2_tile_v1_53 $root -part xc7z020clg400-1 -force
} finally {
 if {[file exists $seed]} {file rename $seed $sdk}
}
set_property target_language Verilog [current_project]
set_property ip_repo_paths [list $root/ip_repo] [current_project]
update_ip_catalog
add_files [glob $root/rtl/*.v]
add_files -fileset constrs_1 $root/constraints/pynq_z2.xdc
create_bd_design system
set ps7 [create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 ps7]
source $root/scripts/ps7_preset.tcl
set_property -dict [list CONFIG.PCW_USE_M_AXI_GP0 {1} CONFIG.PCW_EN_CLK0_PORT {1} CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} CONFIG.PCW_EN_CLK1_PORT {1} CONFIG.PCW_FPGA1_PERIPHERAL_FREQMHZ {200} CONFIG.PCW_EN_CLK2_PORT {0} CONFIG.PCW_EN_CLK3_PORT {0}] $ps7
make_bd_intf_pins_external [get_bd_intf_pins ps7/DDR]
make_bd_intf_pins_external [get_bd_intf_pins ps7/FIXED_IO]
set_property name DDR [get_bd_intf_ports DDR_0]
set_property name FIXED_IO [get_bd_intf_ports FIXED_IO_0]
create_bd_cell -type ip -vlnv digilentinc.com:ip:dvi2rgb:1.7 hdmi_rx
set_property -dict [list CONFIG.kEmulateDDC {true} CONFIG.kEdidFileName {720p_edid.data} CONFIG.kRstActiveHigh {false} CONFIG.kClkRange {2} CONFIG.kAddBUFG {true} CONFIG.kEnableSerialClkOutput {true}] [get_bd_cells hdmi_rx]
create_bd_cell -type ip -vlnv digilentinc.com:ip:rgb2dvi:1.2 hdmi_tx
# kGenerateSerialClk=true: the TX encoder generates its OWN TMDS serial clock from the
# recovered PixelClk. Sharing dvi2rgb's recovered SerialClk (a BUFIO in the RX clock
# region) with the TX OSERDES (in a different IO region) is unplaceable on PYNQ-Z2
# (Place 30-99 IO Clock Placer failed). Each side keeps its own serial clock.
# kClkRange=2: for a >=60MHz pixel clock the MMCM must be tuned so its VCO lands in the
# 600-1200MHz operating window (74.25MHz * 10 = 742.5MHz) - DRC PDRC-34 would otherwise
# reject a 371.25MHz VCO (kClkRange=1 -> MULT_F=5).
set_property -dict [list CONFIG.kGenerateSerialClk {true} CONFIG.kClkRange {2} CONFIG.kRstActiveHigh {true}] [get_bd_cells hdmi_tx]
create_bd_cell -type module -reference video_bypass bypass
create_bd_cell -type module -reference status_cdc status
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 zero
set_property CONFIG.CONST_VAL 0 [get_bd_cells zero]
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 one
set_property CONFIG.CONST_VAL 1 [get_bd_cells one]
create_bd_cell -type ip -vlnv xilinx.com:ip:util_vector_logic:2.0 unlock
set_property -dict [list CONFIG.C_OPERATION {not} CONFIG.C_SIZE {1}] [get_bd_cells unlock]
proc net {args} {set pins {};foreach a $args {lappend pins [get_bd_pins $a]};connect_bd_net {*}$pins}
net ps7/FCLK_CLK1 hdmi_rx/RefClk
net ps7/FCLK_CLK0 status/ref_clk bypass/control_clk
net ps7/FCLK_RESET0_N hdmi_rx/aRst_n
net one/dout hdmi_rx/pRst_n
net hdmi_rx/PixelClk bypass/pixel_clk status/pixel_clk hdmi_tx/PixelClk
net hdmi_rx/aPixelClkLckd unlock/Op1 status/locked
net unlock/Res bypass/reset hdmi_tx/aRst
foreach {rx by} {vid_pData rgb_in vid_pVDE de_in vid_pHSync hs_in vid_pVSync vs_in} {net hdmi_rx/$rx bypass/$by}
foreach {by tx} {rgb_out vid_pData de_out vid_pVDE hs_out vid_pHSync vs_out vid_pVSync} {net bypass/$by hdmi_tx/$tx}
net bypass/frame_count status/frame_count
net bypass/format_ok status/format_ok
foreach {pin name dir width} {
hdmi_rx/TMDS_Clk_p hdmi_in_clk_p I 1
hdmi_rx/TMDS_Clk_n hdmi_in_clk_n I 1
hdmi_rx/TMDS_Data_p hdmi_in_data_p I 3
hdmi_rx/TMDS_Data_n hdmi_in_data_n I 3
hdmi_tx/TMDS_Clk_p hdmi_out_clk_p O 1
hdmi_tx/TMDS_Clk_n hdmi_out_clk_n O 1
hdmi_tx/TMDS_Data_p hdmi_out_data_p O 3
hdmi_tx/TMDS_Data_n hdmi_out_data_n O 3
status/sink_hpd hdmi_out_hpd I 1
status/source_hpd hdmi_in_hpd O 1
status/led led O 4} {
 if {$width==1} {set p [create_bd_port -dir $dir $name]} else {set p [create_bd_port -dir $dir -from [expr {$width-1}] -to 0 $name]}
 connect_bd_net $p [get_bd_pins $pin]
}
# IIC interface automatically inserts open-drain IOBUFs in the generated wrapper.
make_bd_intf_pins_external [get_bd_intf_pins hdmi_rx/DDC]
set_property name hdmi_in_ddc [get_bd_intf_ports DDC_0]
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 frame_gpio
set_property -dict [list CONFIG.C_GPIO_WIDTH {32} CONFIG.C_ALL_INPUTS {1} CONFIG.C_IS_DUAL {1} CONFIG.C_GPIO2_WIDTH {32} CONFIG.C_ALL_OUTPUTS_2 {1}] [get_bd_cells frame_gpio]
net status/frame_count_ref frame_gpio/gpio_io_i
net frame_gpio/gpio2_io_o bypass/config_request
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/ps7/M_AXI_GP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins frame_gpio/S_AXI]
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 roi_gpio
set_property -dict [list CONFIG.C_GPIO_WIDTH {32} CONFIG.C_ALL_OUTPUTS {1} CONFIG.C_IS_DUAL {1} CONFIG.C_GPIO2_WIDTH {32} CONFIG.C_ALL_OUTPUTS_2 {1}] [get_bd_cells roi_gpio]
net roi_gpio/gpio_io_o bypass/roi_min_request
net roi_gpio/gpio2_io_o bypass/roi_max_request
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/ps7/M_AXI_GP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins roi_gpio/S_AXI]
foreach gpio {stats0_gpio stats1_gpio stats2_gpio} {
 create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 $gpio
 set_property -dict [list CONFIG.C_GPIO_WIDTH {32} CONFIG.C_ALL_INPUTS {1} CONFIG.C_IS_DUAL {1} CONFIG.C_GPIO2_WIDTH {32} CONFIG.C_ALL_INPUTS_2 {1}] [get_bd_cells $gpio]
 apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/ps7/M_AXI_GP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins $gpio/S_AXI]
}
net bypass/candidate_count_ref stats0_gpio/gpio_io_i
net bypass/bbox_min_ref stats0_gpio/gpio2_io_i
net bypass/bbox_max_ref stats1_gpio/gpio_io_i
net bypass/snapshot_seq_ref stats1_gpio/gpio2_io_i
net bypass/snapshot_config_ref stats2_gpio/gpio_io_i
net bypass/snapshot_status_ref stats2_gpio/gpio2_io_i
foreach gpio {brightness0_gpio brightness1_gpio brightness2_gpio} {
 create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 $gpio
 set_property -dict [list CONFIG.C_GPIO_WIDTH {32} CONFIG.C_ALL_INPUTS {1} CONFIG.C_IS_DUAL {1} CONFIG.C_GPIO2_WIDTH {32} CONFIG.C_ALL_INPUTS_2 {1}] [get_bd_cells $gpio]
 apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/ps7/M_AXI_GP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins $gpio/S_AXI]
}
net bypass/brightness_count_ref brightness0_gpio/gpio_io_i
net bypass/brightness_sum_ref brightness0_gpio/gpio2_io_i
net bypass/brightness_seq_ref brightness1_gpio/gpio_io_i
net bypass/brightness_config_ref brightness1_gpio/gpio2_io_i
net bypass/brightness_min_ref brightness2_gpio/gpio_io_i
net bypass/brightness_max_ref brightness2_gpio/gpio2_io_i
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 crc_gpio
set_property -dict [list CONFIG.C_GPIO_WIDTH {32} CONFIG.C_ALL_INPUTS {1}] [get_bd_cells crc_gpio]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/ps7/M_AXI_GP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins crc_gpio/S_AXI]
net bypass/mask_crc_ref crc_gpio/gpio_io_i
create_bd_cell -type ip -vlnv xilinx.com:ip:ila:6.2 video_ila
# Vivado 2025.2 ILA bd.tcl init explicitly defaults to AXI monitoring. Force
# Native before manual probes, or AXI propagation silently resizes/truncates them.
set_property CONFIG.C_MONITOR_TYPE {Native} [get_bd_cells video_ila]
set_property -dict [list CONFIG.C_NUM_OF_PROBES {13} CONFIG.C_DATA_DEPTH {1024} CONFIG.C_PROBE0_WIDTH {32} CONFIG.C_PROBE1_WIDTH {32} CONFIG.C_PROBE2_WIDTH {16} CONFIG.C_PROBE3_WIDTH {16} CONFIG.C_PROBE4_WIDTH {1} CONFIG.C_PROBE5_WIDTH {1} CONFIG.C_PROBE6_WIDTH {1} CONFIG.C_PROBE7_WIDTH {24} CONFIG.C_PROBE8_WIDTH {3} CONFIG.C_PROBE9_WIDTH {1} CONFIG.C_PROBE10_WIDTH {16} CONFIG.C_PROBE11_WIDTH {16} CONFIG.C_PROBE12_WIDTH {32}] [get_bd_cells video_ila]
net hdmi_rx/PixelClk video_ila/clk
foreach {pin probe} {frame_count 0 frame_pixels 1 frame_lines 2 line_pixels 3 de_out 4 vs_out 5 format_ok 6 rgb_out 7 mode_active 8 window_valid 9 out_x 10 out_y 11 config_active 12} {net bypass/$pin video_ila/probe$probe}
assign_bd_address
set_property offset 0x41200000 [get_bd_addr_segs ps7/Data/SEG_frame_gpio_Reg]
set_property offset 0x41210000 [get_bd_addr_segs ps7/Data/SEG_roi_gpio_Reg]
set_property offset 0x41220000 [get_bd_addr_segs ps7/Data/SEG_stats0_gpio_Reg]
set_property offset 0x41230000 [get_bd_addr_segs ps7/Data/SEG_stats1_gpio_Reg]
set_property offset 0x41240000 [get_bd_addr_segs ps7/Data/SEG_stats2_gpio_Reg]
set_property offset 0x41250000 [get_bd_addr_segs ps7/Data/SEG_brightness0_gpio_Reg]
set_property offset 0x41260000 [get_bd_addr_segs ps7/Data/SEG_brightness1_gpio_Reg]
set_property offset 0x41270000 [get_bd_addr_segs ps7/Data/SEG_brightness2_gpio_Reg]
set_property offset 0x41280000 [get_bd_addr_segs ps7/Data/SEG_crc_gpio_Reg]
source $root/scripts/add_capture.tcl
validate_bd_design
if {[get_property CONFIG.C_EXT_RESET_HIGH [get_bd_cells capture_ready_reset]]!=1 || [get_property CONFIG.C_AUX_RESET_HIGH [get_bd_cells capture_ready_reset]]!=1} {error "Capture FIFO reset polarity incorrect"}
if {[get_property CONFIG.C_MONITOR_TYPE [get_bd_cells video_ila]] ne "Native" || [get_property CONFIG.C_NUM_OF_PROBES [get_bd_cells video_ila]]!=13} {error "ILA is not a 13-probe Native monitor"}
foreach {idx width} {0 32 1 32 2 16 3 16 4 1 5 1 6 1 7 24 8 3 9 1 10 16 11 16 12 32} {
 if {[get_property CONFIG.C_PROBE${idx}_WIDTH [get_bd_cells video_ila]]!=$width} {error "ILA probe$idx width incorrect"}
}
save_bd_design
generate_target all [get_files system.bd]
add_files -norecurse [make_wrapper -files [get_files system.bd] -top]
set_property top system_wrapper [current_fileset]
update_compile_order -fileset sources_1
write_bd_tcl -force $root/scripts/system_generated.tcl
if {[info exists ::env(TILE_PREPARE_ONLY)]} {close_project;exit}
# Two independent IP jobs fit this16GB machine; implementation stays one job.
launch_runs synth_1 -jobs 2
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Synthesis failed"}
launch_runs impl_1 -to_step write_bitstream -jobs 1
wait_on_run impl_1
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



