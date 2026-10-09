# In-memory experiment only; never save back to the frozen V1.31 checkpoint.
set root [file normalize [file join [file dirname [info script]] ..]]
set baseline $root/../pynq_z2_tile_v1_31
set checkpoint $baseline/pynq_z2_tile_v1_31.runs/impl_1/system_wrapper_routed.dcp
set input $baseline/reports/v131/implemented_applied.xdc
set f [open $input r];set contents [read $f];close $f
set kept {};set removed {}
foreach line [split $contents \n] {
 if {[string match {set_clock_groups *} $line]} {lappend removed $line} else {lappend kept $line}
}
if {[llength $removed]!=1 || ![string match {*hdmi_rx_clk*} [lindex $removed 0]]} {error "Unexpected clock groups; review individually"}
set f [open $root/reports/v132/trial_without_clock_group.xdc w];puts $f [join $kept \n];close $f
set f [open $root/reports/v132/removed_clock_group.txt w];puts $f [join $removed \n];close $f
foreach {name constraints} [list roundtrip $input candidate $root/reports/v132/trial_without_clock_group.xdc] {
 open_checkpoint $checkpoint
 reset_timing -invalid
 read_xdc $constraints
 report_clocks -file $root/reports/v132/${name}_clocks.rpt
 report_timing_summary -max_paths 10 -report_unconstrained -file $root/reports/v132/${name}_timing.rpt
 report_clock_interaction -file $root/reports/v132/${name}_interaction.rpt
 report_exceptions -ignored -file $root/reports/v132/${name}_ignored.rpt
 report_cdc -details -file $root/reports/v132/${name}_cdc.rpt
 report_methodology -file $root/reports/v132/${name}_methodology.rpt
 close_design
}
exit
