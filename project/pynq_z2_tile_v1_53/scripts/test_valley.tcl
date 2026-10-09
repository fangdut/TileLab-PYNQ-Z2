set root [file normalize [file join [file dirname [info script]] ..]]
create_project valley_test $root/reports/valley_sim -part xc7z020clg400-1 -force
add_files [list $root/rtl/directional_valley.v $root/rtl/raster_delay.v]
add_files -fileset sim_1 $root/sim/tb_valley.sv
set_property top tb_valley [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$root" -objects [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
close_project
