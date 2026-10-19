set root [file normalize [file join [file dirname [info script]] ..]]
if {![info exists ::env(TILE_SIM_OUT)]} {error "Set TILE_SIM_OUT to a new directory"}
set out [file normalize $::env(TILE_SIM_OUT)]
if {[file exists $out]} {error "Never overwrite evidence"}
create_project selected_v157 $out -part xc7z020clg400-1
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [glob $root/rtl/*.v]
add_files -fileset sim_1 $root/sim/tb_selected_v157.sv
add_files -fileset sim_1 $root/sim/tb_region_identity_v157.sv
set_property top tb_selected_v157 [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$root/reports/v156/integrated_vectors01 -testplusarg RESULT=$out/core_passed.txt" -objects [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
if {![file exists $out/core_passed.txt]} {error "Missing core proof"}
set_property top tb_region_identity_v157 [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg RESULT=$out/identity_passed.txt" -objects [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
if {![file exists $out/identity_passed.txt]} {error "Missing identity proof"}
close_project
