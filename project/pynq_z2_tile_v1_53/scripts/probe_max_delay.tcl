set root [file normalize [file join [file dirname [info script]] ..]]
set outdir $root/reports/v132
open_checkpoint D:/Vivado/pynq_z2_tile_v1_31/pynq_z2_tile_v1_31.runs/impl_1/system_wrapper_routed.dcp
reset_timing -invalid
read_xdc $root/reports/v132/trial_without_clock_group.xdc
set out [open $outdir/probe_max_delay_audit.json w]
puts $out {"placeholder":false}
close $out
set rows {}
set first 1
foreach {name base source_pattern destination_pattern requirement} {
 fifo_read system_i/capture_fifo/inst/gen_fifo.xpm_fifo_axis_inst/xpm_fifo_base_inst/gen_cdc_pntr.rd_pntr_cdc_inst src_gray_ff_reg* {dest_graysync_ff_reg[0]*} 10.000
 fifo_write system_i/capture_fifo/inst/gen_fifo.xpm_fifo_axis_inst/xpm_fifo_base_inst/gen_cdc_pntr.wr_pntr_cdc_inst src_gray_ff_reg* {dest_graysync_ff_reg[0]*} 13.468
 config system_i/bypass/inst/bridge/transfer src_hsdata_ff_reg* dest_hsdata_ff_reg* 53.872
 brightness system_i/bypass/inst/brightness/transfer src_hsdata_ff_reg* dest_hsdata_ff_reg* 10.000
 candidates system_i/bypass/inst/candidates/transfer src_hsdata_ff_reg* dest_hsdata_ff_reg* 10.000
 regions system_i/bypass/inst/regions/cdc src_hsdata_ff_reg* dest_hsdata_ff_reg* 10.000
 descriptor system_i/capture/inst/transfer src_hsdata_ff_reg* dest_hsdata_ff_reg* 10.000
 frame_count system_i/status/inst/snapshot src_hsdata_ff_reg* dest_hsdata_ff_reg* 40.000
} {
 current_instance $base
 set source [get_cells $source_pattern]
 set destination [get_cells $destination_pattern]
 current_instance
 if {[llength $source]==0 || [llength $destination]==0} {error "Missing $name CDC cells"}
 set paths [get_timing_paths -from $source -to $destination -max_paths 2000 -nworst 1]
 set timed {}
 foreach path $paths {lappend timed [get_property ENDPOINT_PIN $path]}
 set constants 0
 foreach cell $destination {
  set dpin [get_pins $cell/D]
  if {[lsearch -exact $timed $dpin]<0} {
   set nets [get_nets -segments -of_objects $dpin]
   set constant 0
   set drivers [get_pins -leaf -of_objects $nets -filter {DIRECTION == OUT}]
   set driver_cells [get_cells -quiet -of_objects $drivers]
   if {[llength $driver_cells]==1 && [get_property REF_NAME $driver_cells] in {GND VCC}} {set constant 1}
   puts "UNTIMED $name $dpin CONSTANT=$constant NETS=$nets"
   if {!$constant} {report_property $nets;error "$name untimed nonconstant destination: $dpin"}
   incr constants
  }
 }
 if {[llength $paths]+$constants!=[llength $destination]} {error "$name endpoint coverage incomplete"}
 set worst 100000
 foreach path $paths {
  set slack [get_property SLACK $path]
  if {$slack<0 || abs([get_property REQUIREMENT $path]-$requirement)>0.001} {error "$name failed max-delay/slack requirement"}
  if {$slack<$worst} {set worst $slack}
 }
 if {$first} {report_timing -from $source -to $destination -max_paths 1 -file $outdir/probe_max_delay_paths.rpt;set first 0} else {report_timing -from $source -to $destination -max_paths 1 -append -file $outdir/probe_max_delay_paths.rpt}
 lappend rows [format {"name":"%s","source_cells":%d,"destination_cells":%d,"timed_endpoints":%d,"constant_endpoints":%d,"requirement_ns":%.3f,"minimum_slack_ns":%.3f} $name [llength $source] [llength $destination] [llength $paths] $constants $requirement $worst]
 puts "PASS $name: [llength $paths] endpoints requirement=$requirement worst_slack=$worst"
}
set out [open $outdir/probe_max_delay_audit.json w]
puts $out "\{\"passed\":true,\"groups\":\[\{[join $rows \},\{]\}\]\}"
close $out
close_design
exit
