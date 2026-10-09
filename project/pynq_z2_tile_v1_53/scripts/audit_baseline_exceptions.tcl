# Read-only diagnostics: inspect the frozen routed baseline without saving it.
set root [file normalize [file join [file dirname [info script]] ..]]
open_checkpoint $root/../pynq_z2_tile_v1_24/pynq_z2_tile_v1_24.runs/impl_1/system_wrapper_routed.dcp
report_exceptions -ignored -file $root/reports/v132/baseline_ignored_exceptions.rpt
report_exceptions -summary -file $root/reports/v132/baseline_exception_summary.rpt
write_xdc -force $root/reports/v132/baseline_applied.xdc
close_design
exit
