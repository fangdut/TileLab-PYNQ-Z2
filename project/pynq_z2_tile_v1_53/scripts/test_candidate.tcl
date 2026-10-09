set root [file normalize [file join [file dirname [info script]] ..]]
create_project candidate [lindex $argv 0] -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files $root/rtl/candidate_stats.v
add_files -fileset sim_1 $root/sim/tb_candidate_stats.sv
set_property top tb_candidate_stats [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
close_project
