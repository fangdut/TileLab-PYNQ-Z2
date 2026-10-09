set root [file normalize [file join [file dirname [info script]] ..]]
set simdir [file normalize [lindex $argv 0]]
create_project sim $simdir -part xc7z020clg400-1 -force
set_property XPM_LIBRARIES {XPM_CDC} [current_project]
add_files [glob $root/rtl/*.v]
add_files -fileset sim_1 [glob $root/sim/*.sv]
foreach top {tb_axis_gray tb_window3x3 tb_sobel3x3 tb_gaussian3x3 tb_video_pipeline tb_status_cdc} {
 set_property top $top [get_filesets sim_1]
 set_property xsim.simulate.runtime all [get_filesets sim_1]
 launch_simulation -simset sim_1 -mode behavioral
 close_sim
}
close_project
