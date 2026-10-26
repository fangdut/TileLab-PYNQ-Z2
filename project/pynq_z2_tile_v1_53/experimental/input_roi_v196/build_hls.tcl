set root [file normalize [file join [file dirname [info script]] ../..]]
foreach key {TILE_ROI_SOURCE TILE_ROI_HLS TILE_ROI_VECTORS} {if {![info exists ::env($key)]} {error "Set $key"}}
set out [file normalize $::env(TILE_ROI_HLS)]
if {[file exists $out]} {error "Use fresh HLS directory"}
file mkdir $out/src
file copy $::env(TILE_ROI_SOURCE) $out/src/texture_integer.cpp
file copy $root/experimental/input_roi_v196/test_roi.cpp $out/src/test_roi.cpp
foreach f {test_model.bin test_rgb.bin test_expected.bin test_fa_expected.bin test_fb_expected.bin} {file copy $::env(TILE_ROI_VECTORS)/$f $out/}
cd $out
open_project $out
open_solution solution -flow_target vivado
set_top texture_integer
add_files src/texture_integer.cpp
add_files -tb src/test_roi.cpp
foreach f {test_model.bin test_rgb.bin test_expected.bin test_fa_expected.bin test_fb_expected.bin} {add_files -tb $f}
set_part xc7z020clg400-1
create_clock -period 10 -name default
set_clock_uncertainty 1
config_compile -pipeline_loops 0
csim_design
csynth_design
cosim_design -rtl verilog -tool xsim
export_design -format ip_catalog -rtl verilog
