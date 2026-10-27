if {![info exists ::env(TILE_HFE_HLS)]} {error "Set TILE_HFE_HLS"}
set out [file normalize $::env(TILE_HFE_HLS)]
open_project $out
open_solution solution
export_design -format ip_catalog -rtl verilog
