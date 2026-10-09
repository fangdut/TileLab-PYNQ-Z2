set root [file normalize [file join [file dirname [info script]] ..]]
create_project -force reset_test [lindex $argv 0] -part xc7z020clg400-1
add_files [list $root/ip_repo/dvi2rgb_v1_7/src/SyncAsync.vhd $root/ip_repo/dvi2rgb_v1_7/src/SyncBase.vhd]
add_files -fileset sim_1 $root/sim/tb_syncbase.vhd
set_property file_type {VHDL 2008} [get_files tb_syncbase.vhd]
set_property top tb_syncbase [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
close_project
