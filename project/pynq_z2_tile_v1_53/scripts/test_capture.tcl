set root [file normalize [file join [file dirname [info script]] ..]]
create_project capture_test $root/reports/capture_sim -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files $root/rtl/frame_capture.v
add_files -fileset sim_1 $root/sim/tb_frame_capture.sv
set_property top tb_frame_capture [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
close_project
