# Read-only inspection of the exact implemented design used through V1.30.
set root [file normalize [file join [file dirname [info script]] ..]]
set out $root/reports/v132
file mkdir $out
open_checkpoint D:/Vivado/pynq_z2_tile_v1_24/pynq_z2_tile_v1_24.runs/impl_1/system_wrapper_routed.dcp
report_cdc -details -file $out/baseline_cdc_details.rpt
report_clocks -file $out/baseline_clocks.rpt
report_timing_summary -file $out/baseline_timing_readback.rpt
close_design
exit
