set root [file normalize [file join [file dirname [info script]] ..]]
if {![info exists ::env(TILE_SIM_OUT)]} {error "Set TILE_SIM_OUT to a new directory"}
set out [file normalize $::env(TILE_SIM_OUT)]
if {[file exists $out]} {error "Never overwrite evidence"}
create_project region_quality $out -part xc7z020clg400-1
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files $root/rtl/region_quality_v157.v
add_files -fileset sim_1 $root/sim/tb_region_quality_v157.sv
set_property top tb_region_quality_v157 [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$root/reports/v157/region_vectors01 -testplusarg RESULT=$out/passed.txt" -objects [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
if {![file exists $out/passed.txt]} {error "Missing proof"}
close_project
