set root [file normalize [file join [file dirname [info script]] ..]]
file mkdir $root/reports/v142
open_checkpoint $root/pynq_z2_tile_v1_53.runs/impl_1/system_wrapper_routed.dcp
foreach {clock period} {clk_fpga_0 10.0 clk_fpga_1 5.0 hdmi_rx_clk 13.468 PixelClk_int 13.468} {
 set object [get_clocks -quiet $clock]
 if {[llength $object]!=1 || abs([get_property PERIOD $object]-$period)>0.001} {error "Missing or wrong implemented clock $clock"}
}
report_clocks -file $root/reports/v142/implemented_clocks.rpt
report_clock_interaction -file $root/reports/v142/implemented_clock_interaction.rpt
report_exceptions -ignored -file $root/reports/v142/implemented_ignored_exceptions.rpt
write_xdc -force $root/reports/v142/implemented_applied.xdc
set out [open $root/reports/v142/reset_netlist.txt w]
set pixel [get_cells -hier -filter {NAME =~ *DecoderResets/PixelResetBridge/SyncAsyncx/oSyncStages_reg*}]
set reference [get_cells -hier -filter {NAME =~ *DecoderResets/ReferenceResetBridge/SyncAsyncx/oSyncStages_reg*}]
set old [get_cells -quiet -hier -filter {NAME =~ *SourceResetBridge*}]
puts $out "PIXEL_REGISTERS [llength $pixel]"
puts $out "REFERENCE_REGISTERS [llength $reference]"
puts $out "OLD_DUPLICATE_BRIDGES [llength $old]"
foreach cell [concat $pixel $reference] {puts $out "$cell [get_property REF_NAME $cell] ASYNC_REG=[get_property ASYNC_REG $cell]"}
close $out
if {[llength $pixel]!=2 || [llength $reference]!=2 || [llength $old]!=0} {error "Shared reset topology did not survive implementation as expected"}
foreach cell [concat $pixel $reference] {
 if {![get_property ASYNC_REG $cell]} {error "Reset synchronizer lost ASYNC_REG"}
}
# These input-register resets now come from their own RefClk domain and must
# be normally timed; they were previously covered by a blanket false path.
set launch [get_cells -hier -filter {NAME =~ *ReferenceResetBridge/SyncAsyncx/oSyncStages_reg*}]
set capture [get_cells -hier -filter {NAME =~ *SyncBaseOvf/iIn_q_reg}]
set paths [get_timing_paths -from $launch -to $capture -max_paths 6]
if {[llength $capture]!=3 || [llength $paths]<3} {error "Expected three normally timed reference reset paths"}
report_timing -from $launch -to $capture -max_paths 6 -file $root/reports/v142/reference_reset_recovery.rpt
foreach path $paths {if {[get_property SLACK $path]<0} {error "Shared reset recovery timing failed"}}
# Check both recovery (setup-like) and removal (hold-like) in BOTH domains.
# A positive recovery report alone would not prove the minimum-delay paths.
foreach {domain source_glob target_glob} {
 reference *ReferenceResetBridge/SyncAsyncx/oSyncStages_reg* *SyncBaseOvf/iIn_q_reg
 pixel *PixelResetBridge/SyncAsyncx/oSyncStages_reg* *SyncBaseRst/iIn_q_reg
} {
 set source [get_cells -hier -filter "NAME =~ $source_glob"]
 set target [get_cells -hier -filter "NAME =~ $target_glob"]
 if {[llength $target]!=3} {error "Expected three $domain source register resets"}
 foreach {delay check_name} {max recovery min removal} {
  set paths [get_timing_paths -delay_type $delay -from $source -to $target -max_paths 6]
  if {[llength $paths]<3} {error "$domain $check_name paths are missing or excepted"}
  foreach path $paths {if {[get_property SLACK $path]<0} {error "$domain $check_name failed"}}
  report_timing -delay_type $delay -from $source -to $target -max_paths 6 -file $root/reports/v142/${domain}_reset_${check_name}.rpt
 }
}
close_design
exit
