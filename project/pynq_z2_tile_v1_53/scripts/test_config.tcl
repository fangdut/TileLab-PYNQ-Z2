set root [file normalize [file join [file dirname [info script]] ..]]
create_project cfg [lindex $argv 0] -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files $root/rtl/config_bridge.v
add_files -fileset sim_1 $root/sim/tb_config_bridge.sv
set_property top tb_config_bridge [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
close_project
