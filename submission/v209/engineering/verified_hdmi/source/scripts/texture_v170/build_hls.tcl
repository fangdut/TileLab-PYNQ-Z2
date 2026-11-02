set root [file normalize [file join [file dirname [info script]] ../..]]
if {![info exists ::env(TILE_TEXTURE_HLS)] || ![info exists ::env(TILE_TEXTURE_VECTORS)]} {error "Set output/vector folders"}
set out [file normalize $::env(TILE_TEXTURE_HLS)]
if {[file exists $out]} {error "Use a fresh output directory"}
file mkdir $out/src
foreach f {texture_integer.cpp test_integer.cpp} {file copy $root/experimental/texture_v170/hls/$f $out/src/}
foreach f {test_model.bin test_rgb.bin test_expected.bin test_fa_expected.bin test_fb_expected.bin} {file copy $::env(TILE_TEXTURE_VECTORS)/$f $out/}
cd $out
open_project $out
open_solution solution -flow_target vivado
set_top texture_integer
add_files src/texture_integer.cpp
add_files -tb src/test_integer.cpp
foreach f {test_model.bin test_rgb.bin test_expected.bin test_fa_expected.bin test_fb_expected.bin} {add_files -tb $f}
set_part xc7z020clg400-1
create_clock -period 10 -name default
set_clock_uncertainty 1
config_compile -pipeline_loops 0
csim_design
csynth_design
cosim_design -rtl verilog -tool xsim
export_design -format ip_catalog -rtl verilog
