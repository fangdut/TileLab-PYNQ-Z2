if {![info exists ::env(TILE_HLS_OUT)]} {error "Set TILE_HLS_OUT"}
set out [file normalize $::env(TILE_HLS_OUT)]
cd $out
open_project $out
open_solution solution
cosim_design -rtl verilog -tool xsim
exit
