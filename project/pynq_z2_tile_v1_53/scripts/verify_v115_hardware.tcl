set root [file normalize [file join [file dirname [info script]] ..]]
open_project $root/pynq_z2_tile_v1_53.xpr
open_run impl_1
# Synthesized MUXF7 cells can inherit the register's name prefix. Count
# actual flip-flop primitives, not every combinational fan-in cell.
set crc_cells [get_cells -hier -filter {NAME =~ *frame_crc_reg* && REF_NAME =~ FD*}]
set index_cells [get_cells -hier -filter {NAME =~ *trailer_index_reg* && REF_NAME =~ FD*}]
set diagnostics [open $root/reports/v132/crc_cell_inventory.txt w]
foreach cell [concat $crc_cells $index_cells] {puts $diagnostics "[get_property NAME $cell] [get_property REF_NAME $cell]"}
close $diagnostics
puts "CRC_CELLS=[llength $crc_cells] INDEX_CELLS=[llength $index_cells]"
set removed_index [get_cells -quiet -hier -filter {NAME =~ *crc_index_reg* && REF_NAME =~ FD*}]
if {[llength $crc_cells]!=32 || [llength $index_cells]!=6 || [llength $removed_index]!=0} {error "Expected 32 CRC bits, 6 shared descriptor-index bits, and no separate CRC-index registers"}
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
if {$setup<0 || $hold<0} {error "Implemented design timing failed"}
set crc_setup [get_property SLACK [get_timing_paths -to $crc_cells -delay_type max -max_paths 1]]
if {$crc_setup<0} {error "CRC feedback path failed timing"}
report_timing -to $crc_cells -max_paths 3 -file $root/reports/v132/crc_timing.rpt
set f [open $root/reports/v132/implemented_clocks.txt w]
foreach c [get_clocks] {puts $f "[get_property NAME $c] : [get_property PERIOD $c] ns"}
close $f
set f [open $root/reports/v132/hardware_crc_check.json w]
puts $f "{\"passed\":true,\"crc_registers\":[llength $crc_cells],\"descriptor_index_registers\":[llength $index_cells],\"setup_wns_ns\":$setup,\"hold_whs_ns\":$hold,\"crc_setup_slack_ns\":$crc_setup}"
close $f
close_project
