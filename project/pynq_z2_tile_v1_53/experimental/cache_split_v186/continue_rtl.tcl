# Continue the exact existing synthesized solution; do not resynthesize it.
set out [file normalize $::env(TILE_PACKED_DETECTOR_HLS)]
if {![file exists $out/solution/syn/report/texture_integer_csynth.xml]} {error "Synthesized solution missing"}
if {[file exists $out/solution/sim/report/texture_integer_cosim.rpt]} {error "Fresh co-simulation required"}
open_project $out
open_solution solution
cosim_design -rtl verilog -tool xsim
export_design -format ip_catalog -rtl verilog
puts "EXISTING_SYNTHESIS_FULL_RTL_AND_IP_FINISHED_NOT_BOARD"
close_project
exit
