set_param general.maxThreads 2
read_verilog -sv {D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53/experimental/packed_pe_v187/packed_pe.sv}
synth_design -top packed_pe -part xc7z020clg400-1 -mode out_of_context
create_clock -period 8.000 [get_ports clk]
report_utilization -file utilization.rpt
report_timing_summary -file synthesis_timing.rpt
set dsp [llength [get_cells -hier -filter {REF_NAME == DSP48E1}]]
set f [open primitive_count.txt w]; puts $f "DSP48E1=$dsp"; close $f
if {$dsp != 1} {error "Expected exactly one shared DSP48E1"}
write_checkpoint -force packed_pe.dcp
exit
