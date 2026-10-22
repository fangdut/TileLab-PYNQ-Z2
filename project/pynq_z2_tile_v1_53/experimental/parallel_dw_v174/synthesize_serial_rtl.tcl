# Resource gate only. No PS, pinout, bitstream export or board programming.
set rtl [file normalize $::env(TILE_PACKED_RTL)]
set out [file normalize $::env(TILE_PACKED_OOC)]
if {[file exists $out]} {error "Fresh OOC output required"}
file mkdir $out
foreach pattern {*.dat *.mem} {foreach f [glob -nocomplain $rtl/$pattern] {file copy $f $out/}}
cd $out
set_param general.maxThreads 1
create_project packed_resource . -in_memory -part xc7z020clg400-1
read_verilog [glob $rtl/*.v]
set f [open $out/clock.xdc w]
puts $f {create_clock -period 10 -name ap_clk [get_ports ap_clk]}
close $f
add_files -fileset constrs_1 $out/clock.xdc
synth_design -top texture_integer -part xc7z020clg400-1 -mode out_of_context
if {[llength [get_clocks -quiet ap_clk]]!=1} {error "Synthesis clock constraint missing"}
report_utilization -file $out/utilization.rpt
report_control_sets -file $out/control_sets.rpt
report_timing_summary -file $out/synthesis_timing.rpt
set dsp [llength [get_cells -hier -filter {REF_NAME == DSP48E1}]]
set bram18 [llength [get_cells -hier -filter {REF_NAME == RAMB18E1}]]
set bram36 [llength [get_cells -hier -filter {REF_NAME == RAMB36E1}]]
set f [open $out/resource_gate.json w]
puts $f "{\"scope\":\"GENERATED_RTL_SYNTHESIS_ONLY_NOT_ROUTED_OR_BOARD\",\"dsp\":$dsp,\"bram18_equivalent\":[expr {$bram18+2*$bram36}]}"
close $f
write_checkpoint -force $out/synthesized.dcp
if {$dsp>220||$bram18+2*$bram36>276} {error "Actual generated RTL exceeds video resource budget"}
puts "PACKED_GENERATED_RTL_RESOURCE_COUNTS_REPORTED_NOT_TIMING_ACCEPTANCE"
exit
