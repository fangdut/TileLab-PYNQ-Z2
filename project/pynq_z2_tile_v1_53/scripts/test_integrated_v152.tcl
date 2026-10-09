set root [file normalize [file join [file dirname [info script]] ..]]
set out $root/reports/v152/integrated_sim
if {[file exists $out]} {error "Never overwrite a simulation run"}
create_project integrated $out -part xc7z020clg400-1
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [glob $root/rtl/*.v]
add_files -fileset sim_1 $root/sim/tb_wide_integrated.sv
set_property top tb_wide_integrated [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$root/reports/v152/integrated_vectors" -objects [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
close_project
