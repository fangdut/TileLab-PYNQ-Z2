set root [file normalize [file join [file dirname [info script]] ..]]
open_project $root/pynq_z2_tile_v1_5.xpr
open_bd_design [get_files system.bd]
delete_bd_objs [get_bd_cells video_ila]
create_bd_cell -type ip -vlnv xilinx.com:ip:ila:6.2 video_ila
set_property CONFIG.C_MONITOR_TYPE {Native} [get_bd_cells video_ila]
set_property -dict [list CONFIG.C_NUM_OF_PROBES {10} CONFIG.C_DATA_DEPTH {1024} CONFIG.C_PROBE0_WIDTH {32} CONFIG.C_PROBE1_WIDTH {32} CONFIG.C_PROBE2_WIDTH {16} CONFIG.C_PROBE3_WIDTH {16} CONFIG.C_PROBE4_WIDTH {1} CONFIG.C_PROBE5_WIDTH {1} CONFIG.C_PROBE6_WIDTH {1} CONFIG.C_PROBE7_WIDTH {24} CONFIG.C_PROBE8_WIDTH {2} CONFIG.C_PROBE9_WIDTH {1}] [get_bd_cells video_ila]
connect_bd_net [get_bd_pins hdmi_rx/PixelClk] [get_bd_pins video_ila/clk]
foreach {pin probe} {frame_count 0 frame_pixels 1 frame_lines 2 line_pixels 3 de_out 4 vs_out 5 format_ok 6 rgb_out 7 mode_active 8 window_valid 9} {
 connect_bd_net [get_bd_pins bypass/$pin] [get_bd_pins video_ila/probe$probe]
}
validate_bd_design
if {[get_property CONFIG.C_MONITOR_TYPE [get_bd_cells video_ila]] ne "Native" || [get_property CONFIG.C_NUM_OF_PROBES [get_bd_cells video_ila]]!=10} {error "ILA monitor type/count changed"}
foreach {idx width} {0 32 1 32 2 16 3 16 4 1 5 1 6 1 7 24 8 2 9 1} {
 if {[get_property CONFIG.C_PROBE${idx}_WIDTH [get_bd_cells video_ila]]!=$width} {error "ILA probe$idx width incorrect"}
}
save_bd_design
generate_target all [get_files system.bd]
write_bd_tcl -force $root/scripts/system_generated.tcl
if {[llength [get_runs -quiet system_video_ila_0_synth_1]]} {reset_run system_video_ila_0_synth_1}
reset_run synth_1
close_project
source $root/scripts/rebuild.tcl
