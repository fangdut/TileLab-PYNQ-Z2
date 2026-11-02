# Preserve initial failure and optimize the same routed logical design.
# No clock changes, blanket CDC exceptions, HLS changes or extra latency.
set hw [file normalize $::env(TILE_TEXTURE_HW)]
set repair [file normalize $::env(TILE_TEXTURE_REPAIR)]
set pl_clock_mhz 100
set f [open $hw/implementation_status.json r];set initial_status [read $f];close $f
if {![regexp {"pl_clock_mhz":\s*([0-9.]+)} $initial_status _ pl_clock_mhz] || $pl_clock_mhz ni {50 50.0 100 100.0 125 125.0}} {error "Unknown initial physical clock"}
set_param general.maxThreads 4
open_project $hw/texture_v170.xpr
open_checkpoint $hw/texture_v170.runs/impl_1/system_wrapper_routed.dcp
source $hw/physical_scripts/constrain_video_cdc.tcl
phys_opt_design -directive AggressiveExplore
route_design -directive Explore
report_timing_summary -file $repair/timing_summary.rpt
report_clocks -file $repair/clocks.rpt
report_utilization -file $repair/utilization.rpt
report_cdc -details -file $repair/video_cdc.rpt
report_bus_skew -file $repair/bus_skew.rpt
report_exceptions -file $repair/video_exceptions.rpt
report_drc -file $repair/drc.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
set errors [llength [get_drc_violations -filter {SEVERITY == Error}]]
set dsp [llength [get_cells -hier -filter {REF_NAME == DSP48E1}]]
set clocks [get_clocks clk_fpga_0]
if {[llength $clocks]!=1} {error "Missing actual PL clock in repair"}
set actual_period [get_property PERIOD $clocks]
if {abs($actual_period-1000.0/$pl_clock_mhz)>0.001} {error "Repair changed the clock"}
set actual_mhz [expr {1000.0/$actual_period}]
set f [open $repair/implementation_status.json w]
puts $f "{\"setup_slack_ns\":$setup,\"hold_slack_ns\":$hold,\"drc_errors\":$errors,\"pl_clock_mhz\":$actual_mhz,\"pl_clock_period_ns\":$actual_period,\"dsp\":$dsp,\"postroute_physical_repair\":true}"
close $f
write_checkpoint -force $repair/after_physical_optimization.dcp
if {$setup<0||$hold<0||$errors||$dsp>220} {error "Postroute repair fails synchronous timing/DRC/capacity; export blocked"}
set f [open $repair/bus_skew.rpt r];set proof [read $f];close $f
if {[regexp -nocase {VIOLATED} $proof] || [regexp -all {Slack\s+\(MET\)} $proof]<2 || ![string match *rd_pntr_cdc_inst/src_gray_ff_reg* $proof] || ![string match *wr_pntr_cdc_inst/src_gray_ff_reg* $proof]} {error "Both FIFO Gray-bus skew constraints must pass"}
write_checkpoint -force $hw/video_accepted.dcp
write_bitstream -force $hw/texture_v170.runs/impl_1/system_wrapper.bit
write_hw_platform -fixed -include_bit -force -file $hw/system.xsa
if {![file exists $hw/system.bit]} {file copy $hw/texture_v170.runs/impl_1/system_wrapper.bit $hw/system.bit}
foreach name {timing_summary.rpt clocks.rpt utilization.rpt video_cdc.rpt bus_skew.rpt video_exceptions.rpt drc.rpt implementation_status.json} {
 file copy -force $repair/$name $hw/$name
}
puts "TEXTURE_VIDEO_POSTROUTE_REPAIR_PASSED"
exit
