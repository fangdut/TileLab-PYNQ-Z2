# Isolated inference platform. No video capture/classifier from earlier builds.
set root [file normalize [file join [file dirname [info script]] ../..]]
foreach n {TILE_TEXTURE_HW TILE_TEXTURE_HLS} {if {![info exists ::env($n)]} {error "Missing $n"}}
set out [file normalize $::env(TILE_TEXTURE_HW)]
set hls [file normalize $::env(TILE_TEXTURE_HLS)]
set video [info exists ::env(TILE_TEXTURE_VIDEO)]
if {[file exists $out]} {error "Refusing to overwrite hardware build"}
set report $hls/solution/sim/report/texture_integer_cosim.rpt
set f [open $report r];set proof [read $f];close $f
if {![regexp {Verilog\s*\|\s*Pass} $proof]} {error "RTL co-simulation did not pass"}
set f [open $hls/src/texture_integer.cpp rb];set built [read $f];close $f
set source $root/experimental/texture_v170/hls/texture_integer.cpp
# A named, tracked snapshot lets the verified baseline build while the next
# memory-scheduling revision is developed. Byte equality remains mandatory.
set frozen $root/experimental/texture_v170/hls/frozen/[file tail $hls].cpp
if {[file exists $frozen]} {set source $frozen}
set f [open $source rb];set current [read $f];close $f
if {$built ne $current} {error "HLS source differs from current source"}
set_param general.maxThreads 4
create_project texture_v170 $out -part xc7z020clg400-1
if {[info exists ::env(TILE_TEXTURE_IP_CACHE)]} {
 file copy [file normalize $::env(TILE_TEXTURE_IP_CACHE)] $out/ip_cache
 config_ip_cache -use_cache_location $out/ip_cache
}
file copy $hls/src/texture_integer.cpp $out/texture_integer_source.cpp
file copy $report $out/hls_cosim.rpt
set_property target_language Verilog [current_project]
set f [open $out/config.xdc w]
puts $f {set_property CFGBVS VCCO [current_design]}
puts $f {set_property CONFIG_VOLTAGE 3.3 [current_design]}
close $f
add_files -fileset constrs_1 $out/config.xdc
set repositories [list $hls/solution/impl/ip]
if {$video} {
 lappend repositories $root/ip_repo
 add_files [glob $root/experimental/video_v171/rtl/*.sv $root/experimental/video_v171/rtl/*.v]
 # Only constrain external video pins which are present on this top.
 set f [open $root/constraints/pynq_z2.xdc r];set lines [split [read $f] "\n"];close $f
 set f [open $out/video.xdc w]
 foreach line $lines {if {[regexp {hdmi_in_|hdmi_out_(clk|data)} $line]} {puts $f $line}}
 close $f
 add_files -fileset constrs_1 $out/video.xdc
}
set_property ip_repo_paths $repositories [current_project]
update_ip_catalog
create_bd_design system
set ps7 [create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 ps7]
source $root/scripts/ps7_preset.tcl
set_property -dict [list CONFIG.PCW_USE_M_AXI_GP0 {1} CONFIG.PCW_USE_S_AXI_HP0 {1} CONFIG.PCW_EN_CLK0_PORT {1} CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} CONFIG.PCW_EN_CLK1_PORT {0} CONFIG.PCW_EN_CLK2_PORT {0} CONFIG.PCW_EN_CLK3_PORT {0}] $ps7
if {$video} {set_property -dict [list CONFIG.PCW_USE_S_AXI_HP1 {1} CONFIG.PCW_EN_CLK1_PORT {1} CONFIG.PCW_FPGA1_PERIPHERAL_FREQMHZ {200}] $ps7}
make_bd_intf_pins_external [get_bd_intf_pins ps7/DDR]
make_bd_intf_pins_external [get_bd_intf_pins ps7/FIXED_IO]
set_property name DDR [get_bd_intf_ports DDR_0]
set_property name FIXED_IO [get_bd_intf_ports FIXED_IO_0]
create_bd_cell -type ip -vlnv xilinx.com:hls:texture_integer:1.0 infer
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 identity
set_property -dict [list CONFIG.C_GPIO_WIDTH {32} CONFIG.C_ALL_INPUTS {1}] [get_bd_cells identity]
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 build_id
set_property -dict [list CONFIG.CONST_WIDTH {32} CONFIG.CONST_VAL {385875969}] [get_bd_cells build_id]
connect_bd_net [get_bd_pins build_id/dout] [get_bd_pins identity/gpio_io_i]
create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 control_fabric
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {2} CONFIG.NUM_CLKS {1}] [get_bd_cells control_fabric]
create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 memory_fabric
set_property -dict [list CONFIG.NUM_SI {4} CONFIG.NUM_MI {1} CONFIG.NUM_CLKS {1}] [get_bd_cells memory_fabric]
create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 resets
set_property -dict [list CONFIG.C_EXT_RESET_HIGH {0} CONFIG.C_AUX_RESET_HIGH {0}] [get_bd_cells resets]
foreach {name value} {zero 0 one 1} {
 create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 $name
 set_property CONFIG.CONST_VAL $value [get_bd_cells $name]
}
proc intf {a b} {connect_bd_intf_net [get_bd_intf_pins $a] [get_bd_intf_pins $b]}
intf ps7/M_AXI_GP0 control_fabric/S00_AXI
intf control_fabric/M00_AXI identity/S_AXI
intf control_fabric/M01_AXI infer/s_axi_control
intf memory_fabric/M00_AXI ps7/S_AXI_HP0
set n 0
foreach p {m_axi_modelmem m_axi_workmem m_axi_inputmem m_axi_outmem} {
 intf infer/$p [format "memory_fabric/S%02d_AXI" $n]
 incr n
}
foreach p {ps7/M_AXI_GP0_ACLK ps7/S_AXI_HP0_ACLK control_fabric/aclk memory_fabric/aclk identity/s_axi_aclk infer/ap_clk resets/slowest_sync_clk} {
 connect_bd_net [get_bd_pins ps7/FCLK_CLK0] [get_bd_pins $p]
}
connect_bd_net [get_bd_pins ps7/FCLK_RESET0_N] [get_bd_pins resets/ext_reset_in]
# Both reset inputs are ACTIVE_LOW. Unused auxiliary reset must stay HIGH.
connect_bd_net [get_bd_pins one/dout] [get_bd_pins resets/dcm_locked] [get_bd_pins resets/aux_reset_in]
connect_bd_net [get_bd_pins zero/dout] [get_bd_pins resets/mb_debug_sys_rst]
connect_bd_net [get_bd_pins resets/peripheral_aresetn] [get_bd_pins identity/s_axi_aresetn] [get_bd_pins infer/ap_rst_n]
connect_bd_net [get_bd_pins resets/interconnect_aresetn] [get_bd_pins control_fabric/aresetn] [get_bd_pins memory_fabric/aresetn]
if {$video} {source $root/scripts/texture_v170/add_video.tcl}
assign_bd_address
set_property offset 0x41200000 [get_bd_addr_segs ps7/Data/SEG_identity_Reg]
set_property offset 0x43C10000 [get_bd_addr_segs ps7/Data/SEG_infer_Reg]
if {$video} {
 set_property offset 0x43C20000 [get_bd_addr_segs ps7/Data/SEG_video_regs_reg0]
 # Each AXI master has its own address space. Updating PS addresses alone
 # leaves the hardware scheduler at incompatible auto-assigned addresses.
 foreach {name offset} {identity_Reg 0x41200000 infer_Reg 0x43C10000 video_regs_reg0 0x43C20000} {
  set_property offset $offset [get_bd_addr_segs pipeline/m_axi_control/SEG_$name]
 }
}
validate_bd_design
save_bd_design
if {[info exists ::env(TILE_TEXTURE_PREPARE_ONLY)]} {puts "TEXTURE_VIDEO_BLOCK_DESIGN_PREPARED";close_project;exit}
generate_target all [get_files system.bd]
make_wrapper -files [get_files system.bd] -top
add_files $out/texture_v170.gen/sources_1/bd/system/hdl/system_wrapper.v
set_property top system_wrapper [current_fileset]
set jobs [expr {$video?1:4}]
launch_runs synth_1 -jobs $jobs
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Synthesis failed"}
launch_runs impl_1 -to_step write_bitstream -jobs $jobs
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {error "Implementation failed"}
open_run impl_1
report_timing_summary -file $out/timing_summary.rpt
report_clocks -file $out/clocks.rpt
report_utilization -file $out/utilization.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
report_drc -file $out/drc.rpt
set errors [llength [get_drc_violations -filter {SEVERITY == Error}]]
set f [open $out/implementation_status.json w]
puts $f "{\"setup_slack_ns\":$setup,\"hold_slack_ns\":$hold,\"drc_errors\":$errors,\"pl_clock_mhz\":100}"
close $f
if {$setup<0 || $hold<0 || $errors} {error "Timing/DRC failed"}
write_hw_platform -fixed -include_bit -force -file $out/system.xsa
file copy $out/texture_v170.runs/impl_1/system_wrapper.bit $out/system.bit
puts "TEXTURE_V170_IMPLEMENTATION_PASSED"
exit
