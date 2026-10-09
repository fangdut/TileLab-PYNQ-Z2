set root [file normalize [file join [file dirname [info script]] ..]]
create_project -in_memory -part xc7z020clg400-1
add_files $root/rtl/axis_gray.v
set_property top axis_gray [current_fileset]
ipx::package_project -root_dir $root/ip_repo/axis_gray_1_0 -vendor user.org -library user -taxonomy /Video_Imaging -import_files -set_current true
set core [ipx::current_core]
set_property name axis_gray $core
set_property display_name {AXI4 Stream RGB grayscale and bypass} $core
set_property description {24-bit RGB elastic stream stage with frame and line markers. Mode must be constant during a frame.} $core
set_property version 1.0 $core
ipx::infer_bus_interfaces xilinx.com:interface:axis_rtl:1.0 $core
ipx::associate_bus_interfaces -busif s_axis -clock aclk $core
ipx::associate_bus_interfaces -busif m_axis -clock aclk $core
ipx::create_xgui_files $core
ipx::update_checksums $core
ipx::check_integrity $core
ipx::save_core $core
close_project
