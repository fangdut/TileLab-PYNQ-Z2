set_param general.maxThreads 2
cd {D:/Vivado/TileLab_RealPhotos_20261020/v170_hls75/solution/syn/verilog}
read_verilog [glob *.v]
synth_design -top texture_integer -part xc7z020clg400-1 -mode out_of_context -flatten_hierarchy rebuilt
create_clock -name ap_clk -period 10 [get_ports ap_clk]
report_utilization -file {D:/Vivado/TileLab_RealPhotos_20261020/v190_ooc75_01/utilization.rpt}
report_utilization -hierarchical -file {D:/Vivado/TileLab_RealPhotos_20261020/v190_ooc75_01/hierarchy.rpt}
report_timing_summary -file {D:/Vivado/TileLab_RealPhotos_20261020/v190_ooc75_01/timing_synthesis_only.rpt}
write_checkpoint {D:/Vivado/TileLab_RealPhotos_20261020/v190_ooc75_01/detector_synth.dcp}
puts "PAIRED_DETECTOR_OOC_SYNTH_PASS_NOT_ROUTED_OR_BOARD"
exit
