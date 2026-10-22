set_param general.maxThreads 2
open_checkpoint D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/texture_v170.runs/system_infer_0_synth_1/system_infer_0.dcp
set f [open D:/Vivado/TileLab_RealPhotos_20261020/v179_dsp_cells01.txt w]
foreach cell [get_cells -hier -filter {REF_NAME == DSP48E1}] {puts $f $cell}
close $f
puts "READ_ONLY_DSP_BREAKDOWN_FINISHED"
close_design
exit
