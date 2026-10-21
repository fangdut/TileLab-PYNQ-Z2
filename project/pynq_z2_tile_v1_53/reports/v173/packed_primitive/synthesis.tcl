create_project packed_check . -in_memory -part xc7z020clg400-1
read_verilog -sv D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53/experimental/packed_mac_v173/packed_product.sv
synth_design -top packed_product -part xc7z020clg400-1 -mode out_of_context
create_clock -period 10 [get_ports clk]
set dsps [llength [get_cells -hier -filter {REF_NAME =~ DSP48*}]]
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
if {$dsps != 1} {error "Packed prototype requires exactly one DSP; actual=$dsps"}
puts "PACKED_DSP_TWO_INT8_OR_NEAREST_SINGLE_DSP_SYNTH_PASS DSP=$dsps"
exit
