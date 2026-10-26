set root [file normalize [file join [file dirname [info script]] ../..]]
foreach key {TILE_PRE_HLS TILE_PRE_VECTORS} {if {![info exists ::env($key)]} {error "Set $key"}}
set out [file normalize $::env(TILE_PRE_HLS)]
if {[file exists $out]} {error "Fresh HLS directory required"}
file mkdir $out/src
foreach f {preprocess_integer.cpp test_preprocess.cpp} {file copy $root/experimental/hfenet_v197/$f $out/src/}
foreach f {rgb.bin channels.bin} {file copy $::env(TILE_PRE_VECTORS)/$f $out/}
cd $out
open_project $out
open_solution solution -flow_target vivado
set_top preprocess_integer
add_files src/preprocess_integer.cpp
add_files -tb src/test_preprocess.cpp
foreach f {rgb.bin channels.bin} {add_files -tb $f}
set_part xc7z020clg400-1
create_clock -period 10 -name default
set_clock_uncertainty 1
config_compile -pipeline_loops 0
csim_design
csynth_design
cosim_design -rtl verilog -tool xsim
export_design -format ip_catalog -rtl verilog
