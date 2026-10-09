set root [file normalize [file join [file dirname [info script]] ..]]
create_project gate_test $root/reports/v15/gate_band_sim -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [list $root/rtl/frame_capture_sg.v $root/rtl/product_tracker.v]
add_files -fileset sim_1 $root/sim/tb_gate_band_v15.sv
set_property top tb_gate_band_v15 [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
set f [open $root/reports/v15/gate_band_sim/gate_test.sim/sim_1/behav/xsim/simulate.log r]
set log [read $f];close $f
if {[string match {*Fatal:*} $log] || ![string match {*PASS 64-column gate*} $log]} {error "Gate band simulation failed"}
close_project
