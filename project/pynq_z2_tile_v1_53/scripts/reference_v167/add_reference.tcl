# Full-frame DDR score engine, in the same image as HDMI and Ethernet.
create_bd_cell -type ip -vlnv xilinx.com:hls:reference_frame:1.0 reference
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/ps7/M_AXI_GP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins reference/s_axi_control]
foreach port {m_axi_readmem m_axi_writemem} {
 apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master "/reference/$port" Slave {/ps7/S_AXI_HP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins reference/$port]
}
assign_bd_address
set_property offset 0x43C10000 [get_bd_addr_segs ps7/Data/SEG_reference_Reg]
