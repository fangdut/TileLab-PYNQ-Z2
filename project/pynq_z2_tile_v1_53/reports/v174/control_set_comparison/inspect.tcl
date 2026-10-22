set_param general.maxThreads 2
open_checkpoint {D:/Vivado/TileLab_RealPhotos_20261020/v173_hw04/texture_v170.runs/system_infer_0_synth_1/system_infer_0.dcp}
report_control_sets -verbose -file {D:/Vivado/TileLab_RealPhotos_20261020/v174_control_sets01/hls39_control_sets.rpt}
report_utilization -hierarchical -file {D:/Vivado/TileLab_RealPhotos_20261020/v174_control_sets01/hls39_hierarchy.rpt}
close_design
open_checkpoint {D:/Vivado/TileLab_RealPhotos_20261020/v174_hw01/texture_v170.runs/system_infer_0_synth_1/system_infer_0.dcp}
report_control_sets -verbose -file {D:/Vivado/TileLab_RealPhotos_20261020/v174_control_sets01/hls42_control_sets.rpt}
report_utilization -hierarchical -file {D:/Vivado/TileLab_RealPhotos_20261020/v174_control_sets01/hls42_hierarchy.rpt}
close_design
open_checkpoint {D:/Vivado/TileLab_RealPhotos_20261020/v174_ooc43/synthesized.dcp}
report_control_sets -verbose -file {D:/Vivado/TileLab_RealPhotos_20261020/v174_control_sets01/hls43_frp_control_sets.rpt}
report_utilization -hierarchical -file {D:/Vivado/TileLab_RealPhotos_20261020/v174_control_sets01/hls43_frp_hierarchy.rpt}
close_design
puts "CONTROL_SET_COMPARISON_COMPLETE"
exit
