set root [file normalize [file join [file dirname [info script]] ..]]
create_project detect [lindex $argv 0] -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [glob $root/rtl/*.v]
add_files -fileset sim_1 $root/sim/tb_quad_legacy_detection.sv
set_property top tb_quad_legacy_detection [get_filesets sim_1]
if {[llength $argv]>2} {set_property generic {W=1280 H=720 HT=1650 VT=750 TOP=25} [get_filesets sim_1]}
set_property -name xsim.simulate.xsim.more_options -value "-testplusarg ROOT=[lindex $argv 1]" -objects [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
close_project
