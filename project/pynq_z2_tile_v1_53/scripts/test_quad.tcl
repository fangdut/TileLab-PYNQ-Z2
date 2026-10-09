set root [file normalize [file join [file dirname [info script]] ..]]
create_project quad_test $root/reports/v132/quad_sim -part xc7z020clg400-1 -force
add_files [list $root/rtl/raster_morph.v $root/rtl/window3x3.v $root/rtl/raster_delay.v]
add_files -fileset sim_1 $root/sim/tb_quad_hysteresis.sv
set_property top tb_quad_hysteresis [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$root" -objects [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
close_project
