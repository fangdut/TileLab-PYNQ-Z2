set root [file normalize [file join [file dirname [info script]] ..]]
open_checkpoint $root/pynq_z2_tile_v1_5.runs/system_capture_0_synth_1/system_capture_0.dcp
set complete [get_cells -hier -filter {NAME =~ *best_complete*}]
set f [open $root/reports/v14/capture_netlist_audit.txt w]
puts $f "best_complete_cells=[llength $complete]"
puts $f $complete
close $f
if {[llength $complete]<1} {error "Capture checkpoint predates completeness-ranking change; rebuild required"}
close_design
