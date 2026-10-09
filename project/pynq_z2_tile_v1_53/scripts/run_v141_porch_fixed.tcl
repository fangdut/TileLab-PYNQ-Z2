set root [file normalize [file join [file dirname [info script]] ..]]
set output $root/reports/v141/porch_fixed
file mkdir $output
cd $output
create_project porch_fixed $output/project -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [list $root/rtl/region_grid.v $root/rtl/frame_capture_sg.v $root/rtl/product_tracker.v]
add_files -fileset sim_1 $root/sim/tb_capture_region_porch_fixed.sv
set_property top tb_capture_region_porch_fixed [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
# No add_wave/log_wave: numeric traces only; do not record per-pixel waveforms.
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
launch_simulation
close_sim
set simdir $output/project/porch_fixed.sim/sim_1/behav/xsim
foreach name {simulate.log packets.csv regions.csv boundaries.csv descriptors.csv} {
 if {[file exists $simdir/$name]} {file copy -force $simdir/$name $output/$name}
}
set fd [open $output/simulate.log r]
set log [read $fd];close $fd
close_project
if {[string match {*Fatal:*} $log] || ![string match {*PASS V141 PORCH FIXED:*} $log]} {
 error "Porch fixed regression did not finish expected assertions"
}
