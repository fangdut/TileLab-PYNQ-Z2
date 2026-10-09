set root [file normalize [file join [file dirname [info script]] ..]]
create_project weak_test $root/reports/weak_sim -part xc7z020clg400-1 -force
add_files [list $root/rtl/raster_morph.v $root/rtl/window3x3.v $root/rtl/raster_delay.v]
add_files -fileset sim_1 $root/sim/tb_weak_hysteresis.sv
set_property top tb_weak_hysteresis [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$root" -objects [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
close_project
