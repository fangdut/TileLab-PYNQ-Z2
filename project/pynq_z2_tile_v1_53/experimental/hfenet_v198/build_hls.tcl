set here [file normalize [file dirname [info script]]]
foreach key {TILE_HFE_HLS TILE_HFE_VECTORS} {if {![info exists ::env($key)]} {error "Set $key"}}
set out [file normalize $::env(TILE_HFE_HLS)]
if {[file exists $out]} {error "Fresh HLS output required"}
file mkdir $out/src
foreach name {texture_integer.cpp contract.hpp norm_math.hpp test_frame.cpp} {file copy $here/$name $out/src/}
set files {model1.bin model2.bin rgb.bin expected1.bin expected2.bin work1.bin work2.bin}
foreach f $files {file copy $::env(TILE_HFE_VECTORS)/$f $out/}
cd $out
open_project $out
open_solution solution -flow_target vivado
set_top texture_integer
add_files src/texture_integer.cpp -cflags "-std=c++17"
add_files -tb src/test_frame.cpp -cflags "-std=c++17"
foreach f $files {add_files -tb $f}
set_part xc7z020clg400-1
create_clock -period 20 -name default
set_clock_uncertainty 2
config_compile -pipeline_loops 0
csim_design
csynth_design
if {[info exists ::env(TILE_HFE_SYNTH_ONLY)]} {puts "HFE_SYNTHESIS_ONLY_NOT_RTL_VERIFIED";exit}
cosim_design -rtl verilog -tool xsim
export_design -format ip_catalog -rtl verilog
