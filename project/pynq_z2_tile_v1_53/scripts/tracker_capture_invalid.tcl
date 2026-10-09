set root [file normalize [file join [file dirname [info script]] ..]]
set out $root/reports/v142/tracker_capture_invalid
file mkdir $out
cd $out
create_project tracker_capture $out/project -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [list $root/rtl/product_tracker.v $root/rtl/frame_capture_sg.v]
add_files -fileset sim_1 $root/sim/tb_tracker_capture_invalid.sv
set_property top tb_tracker_capture_invalid [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
launch_simulation
close_sim
set simdir $out/project/tracker_capture.sim/sim_1/behav/xsim
foreach name {simulate.log packets.csv} {file copy -force $simdir/$name $out/$name}
set fd [open $out/simulate.log r];set log [read $fd];close $fd
close_project
if {[string match {*Fatal:*} $log] || ![string match {*PASS V142 INTEGRATED:*} $log]} {error "Fixed invalid-observation policy assertions failed"}
