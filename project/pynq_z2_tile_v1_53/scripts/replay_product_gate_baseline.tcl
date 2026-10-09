# Reproduce the recorded pre-fix experiment using SEALED V1.36 RTL read-only.
# All generated project/simulator files remain below this V1.37 report root.
set root [file normalize [file join [file dirname [info script]] ..]]
set baseline [file normalize [file join $root .. pynq_z2_tile_v1_36]]
set output $root/reports/v137/product_gate_baseline_replay
file mkdir $output
cd $output
create_project product_gate_baseline $output/project -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [list $baseline/rtl/frame_capture_sg.v $baseline/rtl/product_tracker.v]
add_files -fileset sim_1 $root/sim/tb_product_dark_gate.sv
set_property top tb_product_dark_gate [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
launch_simulation
close_sim
set simdir $output/project/product_gate_baseline.sim/sim_1/behav/xsim
set fd [open $simdir/simulate.log r]
set log [read $fd];close $fd
file copy -force $simdir/simulate.log $output/simulate.log
if {[file exists $simdir/frames.csv]} {file copy -force $simdir/frames.csv $output/frames.csv}
close_project
if {[string match {*Fatal:*} $log] || ![string match {*PASS V137 baseline product gate experiment*} $log]} {
 error "Sealed V1.36 baseline replay did not reproduce both expected limitations"
}
