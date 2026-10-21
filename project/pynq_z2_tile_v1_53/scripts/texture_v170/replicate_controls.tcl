# Physical register duplication only: no clock exceptions or extra latency.
# HLS captures >2000 scalar bits with one FSM enable; clone its driver locally.
if {![info exists ::tile_video_cdc_applied] && [llength [get_cells -hier -regexp {.*pipeline/inst/lock_sync_reg.*}]]} {
 source [file join [file dirname [info script]] constrain_video_cdc.tcl]
}
set candidates {}
foreach net [get_nets -hier -filter {NAME =~ *mac_row*ap_CS_fsm_state* || NAME =~ *mac_row*nearest* || NAME =~ *mac_row*depth_read*}] {
 set loads [get_property FLAT_PIN_COUNT $net]
 set limit [expr {[string match *ap_CS_fsm_state* $net]?256:32}]
 if {$loads>$limit} {puts "REPLICATE_CONTROL $net loads=$loads";lappend candidates $net}
}
if {[llength $candidates]} {
 phys_opt_design -force_replication_on_nets $candidates
}
