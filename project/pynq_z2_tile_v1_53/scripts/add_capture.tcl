# Full-resolution B,G,R,mask frame packets -> DDR through HP0.
set_property CONFIG.PCW_USE_S_AXI_HP0 {1} [get_bd_cells ps7]
net ps7/FCLK_CLK0 ps7/S_AXI_HP0_ACLK
create_bd_cell -type module -reference frame_capture capture
net hdmi_rx/PixelClk capture/pixel_clk
net ps7/FCLK_CLK0 capture/control_clk
net bypass/pixel_reset capture/reset
foreach {a b} {capture_rgb rgb capture_de de capture_vs vs capture_mask mask config_active config_word} {net bypass/$a capture/$b}
foreach {a b} {capture_region_boxes region_boxes capture_region_areas region_areas capture_region_seq region_seq capture_region_status region_status} {net bypass/$a capture/$b}
create_bd_cell -type ip -vlnv xilinx.com:ip:axis_data_fifo:2.0 capture_fifo
set_property -dict [list CONFIG.TDATA_NUM_BYTES {4} CONFIG.HAS_TLAST {1} CONFIG.IS_ACLK_ASYNC {1} CONFIG.FIFO_DEPTH {4096} CONFIG.HAS_TKEEP {0}] [get_bd_cells capture_fifo]
net hdmi_rx/PixelClk capture_fifo/s_axis_aclk
net ps7/FCLK_CLK0 capture_fifo/m_axis_aclk
create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 capture_ready_reset
set_property CONFIG.C_AUX_RESET_HIGH {1} [get_bd_cells capture_ready_reset]
net hdmi_rx/PixelClk capture_ready_reset/slowest_sync_clk
net bypass/pixel_reset capture_ready_reset/ext_reset_in
net zero/dout capture_ready_reset/aux_reset_in capture_ready_reset/mb_debug_sys_rst
net one/dout capture_ready_reset/dcm_locked
net capture_ready_reset/peripheral_aresetn capture_fifo/s_axis_aresetn
connect_bd_intf_net [get_bd_intf_pins capture/M_AXIS] [get_bd_intf_pins capture_fifo/S_AXIS]
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_dma:7.1 capture_dma
set_property -dict [list CONFIG.c_include_sg {1} CONFIG.c_sg_include_stscntrl_strm {0} CONFIG.c_include_mm2s {0} CONFIG.c_include_s2mm {1} CONFIG.c_sg_length_width {26} CONFIG.c_m_axi_s2mm_data_width {64} CONFIG.c_s_axis_s2mm_tdata_width {32} CONFIG.c_s2mm_burst_size {64}] [get_bd_cells capture_dma]
connect_bd_intf_net [get_bd_intf_pins capture_fifo/M_AXIS] [get_bd_intf_pins capture_dma/S_AXIS_S2MM]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/ps7/M_AXI_GP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins capture_dma/S_AXI_LITE]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/capture_dma/M_AXI_S2MM} Slave {/ps7/S_AXI_HP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins ps7/S_AXI_HP0]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/capture_dma/M_AXI_SG} Slave {/ps7/S_AXI_HP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins capture_dma/M_AXI_SG]
foreach gpio {capture0_gpio capture1_gpio capture2_gpio capture3_gpio} {
 create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 $gpio
 set_property -dict [list CONFIG.C_GPIO_WIDTH {32} CONFIG.C_ALL_INPUTS {1} CONFIG.C_IS_DUAL {1} CONFIG.C_GPIO2_WIDTH {32} CONFIG.C_ALL_INPUTS_2 {1}] [get_bd_cells $gpio]
 apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/ps7/M_AXI_GP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins $gpio/S_AXI]
}
set_property -dict [list CONFIG.C_ALL_INPUTS_2 {0} CONFIG.C_ALL_OUTPUTS_2 {1}] [get_bd_cells capture0_gpio]
net capture0_gpio/gpio2_io_o capture/request
net capture/cap_seq capture0_gpio/gpio_io_i
net capture/cap_count capture1_gpio/gpio_io_i
net capture/cap_min capture1_gpio/gpio2_io_i
net capture/cap_max capture2_gpio/gpio_io_i
net capture/cap_status capture2_gpio/gpio2_io_i
net capture/cap_config capture3_gpio/gpio_io_i
net capture/cap_status capture3_gpio/gpio2_io_i
assign_bd_address
set_property offset 0x40400000 [get_bd_addr_segs ps7/Data/SEG_capture_dma_Reg]
foreach {name addr} {capture0_gpio 0x41290000 capture1_gpio 0x412A0000 capture2_gpio 0x412B0000 capture3_gpio 0x412C0000} {
 set_property offset $addr [get_bd_addr_segs ps7/Data/SEG_${name}_Reg]
}


create_bd_cell -type module -reference region_axi regions_regs
net bypass/regions_ref regions_regs/snapshot
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/ps7/M_AXI_GP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins regions_regs/S_AXI]
assign_bd_address
set_property offset 0x43C00000 [get_bd_addr_segs ps7/Data/SEG_regions_regs_reg0]
