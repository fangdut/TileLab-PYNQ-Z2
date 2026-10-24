set_param general.maxThreads 2
read_verilog {D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53/experimental/native_pe_v189/shared_mac.v}
synth_design -top shared_mac -part xc7z020clg400-1 -mode out_of_context
create_clock -period 10 [get_ports ap_clk]
report_utilization -file utilization.rpt
report_timing_summary -file synthesis_timing.rpt
report_utilization -hierarchical -file hierarchy.rpt
set dsp [llength [get_cells -hier -filter {REF_NAME == DSP48E1}]]
if {$dsp != 128} {error "Native unit must use128 DSP"}
write_checkpoint unit.dcp
puts "NATIVE_SHARED_MAC_MAPPED_PASS_NOT_DETECTOR_OR_BOARD"
exit
