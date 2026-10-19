set root [file normalize [file join [file dirname [info script]] ..]]
set out $root/reports/v154/rtl_score_sim
if {[file exists $out]} {error "Never overwrite a simulation run"}
create_project ridge_score $out -part xc7z020clg400-1
add_files [list $root/rtl/raster_delay.v $root/rtl/directional_valley.v $root/rtl/directional_ridge_valley.v $root/rtl/ridge_dual_scale_valley.v]
add_files -fileset sim_1 $root/sim/tb_ridge_valley.sv
set_property top tb_ridge_valley [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$root/reports/v154/ridge_vectors" -objects [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
close_project
