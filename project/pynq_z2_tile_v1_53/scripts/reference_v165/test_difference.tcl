set root [file normalize [file join [file dirname [info script]] .. ..]]
set_param general.maxThreads 2
foreach name {TILE_REF_VECTORS TILE_REF_SIM_OUT} {if {![info exists ::env($name)]} {error "Set $name"}}
set out [file normalize $::env(TILE_REF_SIM_OUT)]
if {[file exists $out]} {error "Choose a new simulation directory"}
create_project reference_difference $out -part xc7z020clg400-1
add_files $root/experimental/reference_v165/rtl/reference_difference_v165.v
add_files -fileset sim_1 $root/sim/tb_reference_difference_v165.sv
set_property top tb_reference_difference_v165 [get_filesets sim_1]
set_property xsim.simulate.custom_tcl $root/scripts/product_gate_no_wave.tcl [get_filesets sim_1]
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=$::env(TILE_REF_VECTORS) -testplusarg RESULT=$out/passed.txt" -objects [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
if {![file exists $out/passed.txt]} {error "Missing arithmetic/handshake proof"}
close_project
