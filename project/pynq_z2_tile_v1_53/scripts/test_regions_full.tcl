set root [file normalize [file join [file dirname [info script]] ..]]
create_project region_full_test $root/reports/v141/region_full_sim -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files $root/rtl/region_grid.v
add_files -fileset sim_1 $root/sim/tb_region_full.sv
set_property top tb_region_full [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$root" -objects [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
launch_simulation
close_sim
set f [open $root/reports/v141/region_full_sim/region_full_test.sim/sim_1/behav/xsim/simulate.log r];set log [read $f];close $f
if {[string match {*Fatal:*} $log] || ![string match {*REGION PASS*} $log]} {error "Full-resolution region assertions failed"}
close_project
