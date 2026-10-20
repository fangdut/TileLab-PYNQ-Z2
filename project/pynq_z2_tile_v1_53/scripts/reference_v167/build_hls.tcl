set root [file normalize [file join [file dirname [info script]] ../..]]
if {![info exists ::env(TILE_HLS_OUT)]} {error "Set TILE_HLS_OUT to a new output directory"}
set out [file normalize $::env(TILE_HLS_OUT)]
if {[file exists $out]} {error "Build output exists"}
file mkdir $out/src
file copy $root/experimental/reference_v167/hls/reference_frame.cpp $out/src/
file copy $root/experimental/reference_v167/hls/test_frame.cpp $out/src/
cd $out
open_project $out
open_solution solution -flow_target vivado
set_top reference_frame
add_files src/reference_frame.cpp
add_files -tb src/test_frame.cpp
set_part xc7z020clg400-1
create_clock -period 10 -name default
csim_design
csynth_design
cosim_design -rtl verilog -tool xsim
export_design -format ip_catalog -rtl verilog
exit
