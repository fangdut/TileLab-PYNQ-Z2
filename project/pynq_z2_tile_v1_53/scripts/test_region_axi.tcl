set root [file normalize [file join [file dirname [info script]] ..]]
create_project axi_test $root/reports/region_axi_sim -part xc7z020clg400-1 -force
add_files $root/rtl/region_axi.v
add_files -fileset sim_1 $root/sim/tb_region_axi.sv
set_property top tb_region_axi [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
close_project
