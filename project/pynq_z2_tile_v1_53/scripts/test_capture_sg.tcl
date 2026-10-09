set root [file normalize [file join [file dirname [info script]] ..]]
create_project sg_test $root/reports/v142/sg_sim -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [list $root/rtl/frame_capture_sg.v $root/rtl/product_tracker.v]
add_files -fileset sim_1 $root/sim/tb_capture_sg.sv
set_property top tb_capture_sg [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
launch_simulation
close_sim
set f [open $root/reports/v142/sg_sim/sg_test.sim/sim_1/behav/xsim/simulate.log r]
set log [read $f];close $f
if {[string match {*Fatal:*} $log] || ![string match {*PASS continuous SG*} $log]} {error "SG simulation assertions did not pass"}
close_project
