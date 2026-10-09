set root [file normalize [file join [file dirname [info script]] ..]]
open_project $root/pynq_z2_tile_v1_53.xpr
open_run impl_1
set crc_cells [get_cells -hier -filter {NAME =~ *frame_crc_reg*}]
if {[llength $crc_cells]!=32} {error "Expected exactly 32 PL frame CRC registers"}
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
if {$setup<0 || $hold<0} {error "Implemented design timing failed"}
set crc_setup [get_property SLACK [get_timing_paths -to $crc_cells -delay_type max -max_paths 1]]
if {$crc_setup<0} {error "CRC feedback path failed timing"}
report_timing -to $crc_cells -max_paths 3 -file $root/reports/v132/crc_timing.rpt
set f [open $root/reports/v132/hardware_crc_check.json w]
puts $f "{\"passed\": true, \"crc_registers\": [llength $crc_cells], \"setup_wns_ns\": $setup, \"hold_whs_ns\": $hold, \"crc_setup_slack_ns\": $crc_setup}"
close $f
close_project
