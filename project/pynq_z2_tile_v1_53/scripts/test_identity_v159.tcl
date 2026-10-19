set root [file normalize [file join [file dirname [info script]] ..]]
set out [file normalize $::env(TILE_SIM_OUT)]
if {[file exists $out]} {error "Never overwrite evidence"}
create_project identity_v159 $out -part xc7z020clg400-1
add_files $root/rtl/region_axi.v
add_files -fileset sim_1 $root/sim/tb_region_identity_v159.sv
set_property top tb_region_identity_v159 [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg RESULT=$out/passed.txt" -objects [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
if {![file exists $out/passed.txt]} {error "Missing identity proof"}
close_project
