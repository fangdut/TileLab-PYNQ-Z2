set root [file normalize [file join [file dirname [info script]] ..]]
foreach name {window3x3 sobel3x3 gaussian3x3} {
 create_project -in_memory -part xc7z020clg400-1
 add_files $root/rtl/$name.v
 set_property top $name [current_fileset]
 ipx::package_project -root_dir $root/ip_repo/${name}_1_0 -vendor user.org -library user -taxonomy /Video_Imaging -import_files -set_current true
 set core [ipx::current_core]
 set_property name $name $core
 set_property display_name "V0.5 $name CE-controlled pixel processing" $core
 set_property description {Synchronous clock-enable pipeline. CE freezes all stages; in_valid holes are supported. This interface is not an independent AXI4-Stream ready/valid channel.} $core
 set_property version 1.0 $core
 ipx::create_xgui_files $core
 ipx::update_checksums $core
 ipx::check_integrity $core
 ipx::save_core $core
 close_project
}
