# Add pure-PL single-ROI video ownership around the unchanged detector IP.
# Called before address assignment. PS is used for one-time DDR/clock setup.
create_bd_cell -type module -reference hdmi_detector_pipeline pipeline
create_bd_cell -type module -reference video_regs video_regs
set_property -dict [list CONFIG.NUM_SI {2} CONFIG.NUM_MI {3}] [get_bd_cells control_fabric]
set_property CONFIG.NUM_SI {5} [get_bd_cells memory_fabric]
intf pipeline/m_axi_control control_fabric/S01_AXI
intf control_fabric/M02_AXI video_regs/s_axi
intf pipeline/m_axi_result memory_fabric/S04_AXI
create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 capture_fabric
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {1} CONFIG.NUM_CLKS {1}] [get_bd_cells capture_fabric]
intf pipeline/m_axi_capture capture_fabric/S00_AXI
intf capture_fabric/M00_AXI ps7/S_AXI_HP1
proc net {args} {set pins {};foreach a $args {lappend pins [get_bd_pins $a]};connect_bd_net {*}$pins}
net ps7/FCLK_CLK0 pipeline/control_clk video_regs/clk capture_fabric/aclk ps7/S_AXI_HP1_ACLK
net resets/peripheral_aresetn pipeline/control_resetn video_regs/resetn
net resets/interconnect_aresetn capture_fabric/aresetn
net video_regs/enable pipeline/enable
foreach name {status completed rejected capture_sequence capture_crc fault peak threshold mask_pixels core_sequence core_cycles} {
 net pipeline/$name video_regs/$name
}
create_bd_cell -type ip -vlnv digilentinc.com:ip:dvi2rgb:1.7 hdmi_rx
set_property -dict [list CONFIG.kEmulateDDC {true} CONFIG.kEdidFileName {720p_edid.data} CONFIG.kRstActiveHigh {false} CONFIG.kClkRange {2} CONFIG.kAddBUFG {true} CONFIG.kEnableSerialClkOutput {true}] [get_bd_cells hdmi_rx]
create_bd_cell -type ip -vlnv digilentinc.com:ip:rgb2dvi:1.2 hdmi_tx
set_property -dict [list CONFIG.kGenerateSerialClk {true} CONFIG.kClkRange {2} CONFIG.kRstActiveHigh {false}] [get_bd_cells hdmi_tx]
create_bd_cell -type module -reference video_alarm_border border
create_bd_cell -type ip -vlnv xilinx.com:ip:xlslice:1.0 alarm_bit
set_property -dict [list CONFIG.DIN_WIDTH {32} CONFIG.DIN_FROM {2} CONFIG.DIN_TO {2} CONFIG.DOUT_WIDTH {1}] [get_bd_cells alarm_bit]
create_bd_cell -type ip -vlnv xilinx.com:ip:xlslice:1.0 valid_bit
set_property -dict [list CONFIG.DIN_WIDTH {32} CONFIG.DIN_FROM {3} CONFIG.DIN_TO {3} CONFIG.DOUT_WIDTH {1}] [get_bd_cells valid_bit]
net pipeline/status alarm_bit/Din valid_bit/Din
net alarm_bit/Dout border/alarm
net valid_bit/Dout border/valid
net ps7/FCLK_CLK1 hdmi_rx/RefClk
net ps7/FCLK_RESET0_N hdmi_rx/aRst_n
net one/dout hdmi_rx/pRst_n
net hdmi_rx/PixelClk pipeline/pixel_clk border/pixel_clk hdmi_tx/PixelClk
net hdmi_rx/aPixelClkLckd pipeline/pixel_resetn border/resetn hdmi_tx/aRst_n
net hdmi_rx/vid_pData pipeline/hdmi_rgb border/rgb_in
net hdmi_rx/vid_pVDE pipeline/de border/de_in
net hdmi_rx/vid_pVSync pipeline/vs border/vs_in
net hdmi_rx/vid_pHSync border/hs_in
foreach {a b} {rgb_out vid_pData de_out vid_pVDE hs_out vid_pHSync vs_out vid_pVSync} {net border/$a hdmi_tx/$b}
foreach {pin name dir width} {
 hdmi_rx/TMDS_Clk_p hdmi_in_clk_p I 1
 hdmi_rx/TMDS_Clk_n hdmi_in_clk_n I 1
 hdmi_rx/TMDS_Data_p hdmi_in_data_p I 3
 hdmi_rx/TMDS_Data_n hdmi_in_data_n I 3
 hdmi_tx/TMDS_Clk_p hdmi_out_clk_p O 1
 hdmi_tx/TMDS_Clk_n hdmi_out_clk_n O 1
 hdmi_tx/TMDS_Data_p hdmi_out_data_p O 3
 hdmi_tx/TMDS_Data_n hdmi_out_data_n O 3
 one/dout hdmi_in_hpd O 1
} {
 if {$width==1} {set port [create_bd_port -dir $dir $name]} else {set port [create_bd_port -dir $dir -from [expr {$width-1}] -to 0 $name]}
 connect_bd_net $port [get_bd_pins $pin]
}
make_bd_intf_pins_external [get_bd_intf_pins hdmi_rx/DDC]
set_property name hdmi_in_ddc [get_bd_intf_ports DDC_0]
# An unused board output HPD input and LEDs are deliberately absent.
