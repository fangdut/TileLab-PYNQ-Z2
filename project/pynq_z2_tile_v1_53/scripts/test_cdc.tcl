set root [file normalize [file join [file dirname [info script]] ..]]
create_project -force cdc_test [lindex $argv 0] -part xc7z020clg400-1
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files $root/rtl/status_cdc.v
add_files -fileset sim_1 $root/sim/tb_status_cdc.sv
set_property top tb_status_cdc [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
close_project
