set root [file normalize [file join [file dirname [info script]] ..]]
create_project bbox [lindex $argv 0] -part xc7z020clg400-1 -force
add_files $root/rtl/bbox_overlay.v
add_files -fileset sim_1 $root/sim/tb_bbox.sv
set_property top tb_bbox [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation -simset sim_1 -mode behavioral
close_sim
close_project
