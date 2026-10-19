# Out-of-context synthesis estimate only, not a routed board build.
set root [file normalize [file join [file dirname [info script]] .. ..]]
set_param general.maxThreads 2
if {![info exists ::env(TILE_REF_SYNTH_OUT)]} {error "Set TILE_REF_SYNTH_OUT"}
set out [file normalize $::env(TILE_REF_SYNTH_OUT)]
if {[file exists $out]} {error "Choose a new output directory"}
file mkdir $out
create_project -in_memory -part xc7z020clg400-1
read_verilog $root/experimental/reference_v165/rtl/reference_difference_v165.v
synth_design -top reference_difference_v165 -mode out_of_context -part xc7z020clg400-1
create_clock -name paired_pixel_clk -period 13.468 [get_ports clk]
report_utilization -file $out/utilization.rpt
report_timing_summary -file $out/timing_estimate.rpt
write_checkpoint $out/paired_arithmetic_ooc.dcp
close_project
