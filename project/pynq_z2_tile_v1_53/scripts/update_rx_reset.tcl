set root [file normalize [file join [file dirname [info script]] ..]]
ipx::open_core $root/ip_repo/dvi2rgb_v1_7/component.xml
set core [ipx::current_core]
set_property core_revision 4 $core
ipx::update_checksums $core
ipx::save_core $core
ipx::unload_core $core
open_project $root/pynq_z2_tile_v1_5.xpr
update_ip_catalog -rebuild
open_bd_design [get_files system.bd]
upgrade_bd_cells [get_bd_cells hdmi_rx]
validate_bd_design
save_bd_design
reset_target all [get_files system.bd]
generate_target all [get_files system.bd]
reset_run system_hdmi_rx_0_synth_1
reset_run synth_1
reset_run impl_1
close_project
source $root/scripts/rebuild.tcl
