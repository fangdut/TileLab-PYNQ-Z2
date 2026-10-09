set root [file normalize [file join [file dirname [info script]] ..]]
set output $root/reports/v137/product_gate_experiment
file mkdir $output
cd $output
create_project product_gate_baseline $output/project -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [list $root/rtl/frame_capture_sg.v $root/rtl/product_tracker.v]
add_files -fileset sim_1 $root/sim/tb_product_dark_gate.sv
set_property top tb_product_dark_gate [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
set simdir $output/project/product_gate_baseline.sim/sim_1/behav/xsim
set fd [open $simdir/simulate.log r]
set log [read $fd];close $fd
file copy -force $simdir/simulate.log $output/simulate.log
if {[file exists $simdir/frames.csv]} {file copy -force $simdir/frames.csv $output/frames.csv}
close_project
if {[string match {*Fatal:*} $log] || ![string match {*PASS V137 baseline product gate experiment*} $log]} {
 error "Product gate baseline experiment did not reproduce both expected failures"
}
