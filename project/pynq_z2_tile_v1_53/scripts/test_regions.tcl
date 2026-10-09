set root [file normalize [file join [file dirname [info script]] ..]]
create_project region_test $root/reports/region_sim -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files $root/rtl/region_grid.v
add_files -fileset sim_1 $root/sim/tb_region_grid.sv
set_property top tb_region_grid [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$root" -objects [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
set f [open $root/reports/region_sim/region_test.sim/sim_1/behav/xsim/simulate.log r];set log [read $f];close $f
if {[string match {*Fatal:*} $log] || ![string match {*REGION PASS*} $log]} {error "Region assertions failed"}
close_project
