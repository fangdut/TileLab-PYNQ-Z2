set root [file normalize [file join [file dirname [info script]] ..]]
set output $root/reports/v142/scheduling_boundaries
file mkdir $output
cd $output
create_project scheduling $output/project -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [list $root/rtl/frame_capture_sg.v $root/rtl/product_tracker.v]
add_files -fileset sim_1 $root/sim/tb_capture_scheduling_v141.sv
set_property top tb_capture_scheduling_v141 [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
launch_simulation
close_sim
set simdir $output/project/scheduling.sim/sim_1/behav/xsim
foreach name {simulate.log boundary_packets.csv} {if {[file exists $simdir/$name]} {file copy -force $simdir/$name $output/$name}}
set fd [open $output/simulate.log r];set log [read $fd];close $fd
close_project
if {[string match {*Fatal:*} $log] || ![string match {*PASS V141 scheduling boundaries*} $log]} {error "Scheduling boundary assertions failed"}
