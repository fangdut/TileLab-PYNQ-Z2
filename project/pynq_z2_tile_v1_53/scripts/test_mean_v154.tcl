set root [file normalize [file join [file dirname [info script]] ..]]
set run_id [lindex $argv 0]
if {$run_id eq ""} {set run_id run01}
if {![regexp {^[a-z0-9_-]+$} $run_id]} {error "Invalid run ID"}
set out $root/reports/v154/rtl_mean_sim_$run_id
set vectors [lindex $argv 1]
if {$vectors eq ""} {set vectors $root/reports/v154/mean_vectors}
set vectors [file normalize $vectors]
if {[file exists $out]} {error "Never overwrite a simulation run"}
create_project mean_score $out -part xc7z020clg400-1
add_files [list $root/rtl/raster_delay.v $root/rtl/directional_valley.v $root/rtl/directional_mean_valley.v $root/rtl/mean_dual_scale_valley.v]
add_files -fileset sim_1 $root/sim/tb_mean_valley.sv
set_property top tb_mean_valley [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$vectors -testplusarg RESULT=$out/passed.txt" -objects [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
if {![file exists $out/passed.txt]} {error "Testbench did not produce its success proof; inspect simulation log"}
close_project
