set root [file normalize [file join [file dirname [info script]] ..]]
set run_id [lindex $argv 0]
if {$run_id eq ""} {set run_id run01}
if {![regexp {^[a-z0-9_-]+$} $run_id]} {error "Invalid run ID"}
set out $root/reports/v155/support_integrated_sim_$run_id
set vectors [lindex $argv 1]
if {$vectors eq ""} {set vectors $root/reports/v155/support_integrated_vectors}
set vectors [file normalize $vectors]
if {[file exists $out]} {error "Never overwrite a simulation run"}
create_project integrated $out -part xc7z020clg400-1
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [glob $root/rtl/*.v]
add_files -fileset sim_1 $root/sim/tb_support_integrated_v155.sv
set_property top tb_support_integrated_v155 [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$vectors -testplusarg RESULT=$out/passed.txt" -objects [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
if {![file exists $out/passed.txt]} {error "Testbench did not produce its success proof; inspect simulation log"}
close_project

