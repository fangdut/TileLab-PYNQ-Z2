set root [file normalize [file join [file dirname [info script]] ..]]
set out $root/reports/v142/tracker_invalid_fixed
file mkdir $out
cd $out
create_project tracker_fixed $out/project -part xc7z020clg400-1 -force
add_files $root/rtl/product_tracker.v
add_files -fileset sim_1 $root/sim/tb_tracker_invalid_fixed.sv
set_property top tb_tracker_invalid_fixed [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
launch_simulation
close_sim
set simdir $out/project/tracker_fixed.sim/sim_1/behav/xsim
foreach name {simulate.log observations.csv} {file copy -force $simdir/$name $out/$name}
set fd [open $out/simulate.log r];set log [read $fd];close $fd
close_project
if {[string match {*Fatal:*} $log] || ![string match {*PASS V142 FIXED:*} $log]} {error "Fixed invalid-observation policy assertions failed"}
