set root [file normalize [file join [file dirname [info script]] ..]]
create_project -force capture_integration $root/reports/capture_integration -part xc7z020clg400-1
set_property XPM_LIBRARIES {XPM_CDC XPM_MEMORY XPM_FIFO} [current_project]
add_files $root/rtl/frame_capture.v
set base $root/pynq_z2_tile_v1_5.gen/sources_1/bd/system/ip
foreach ip {system_capture_ready_reset_0 system_capture_fifo_0} {
 if {![file exists $base/$ip/${ip}_sim_netlist.v]} {error "Generated functional netlist not ready: $ip"}
 add_files $base/$ip/${ip}_sim_netlist.v
}
add_files -fileset sim_1 $root/sim/tb_capture_integration.sv
set_property top tb_capture_integration [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
close_project
