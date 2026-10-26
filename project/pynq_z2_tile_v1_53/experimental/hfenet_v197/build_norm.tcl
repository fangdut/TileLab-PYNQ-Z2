set root [file normalize [file join [file dirname [info script]] ../..]]
foreach key {TILE_NORM_HLS TILE_NORM_VECTORS} {if {![info exists ::env($key)]} {error "Set $key"}}
set out [file normalize $::env(TILE_NORM_HLS)]
if {[file exists $out]} {error "Fresh HLS directory required"}
file mkdir $out/src
foreach f {norm_integer.cpp test_norm.cpp} {file copy $root/experimental/hfenet_v197/$f $out/src/}
set files {params.bin coeff.bin pixels.bin output.bin params2.bin coeff2.bin pixels2.bin output2.bin coefficient_params.bin coefficient_expected.bin}
foreach f $files {file copy $::env(TILE_NORM_VECTORS)/$f $out/}
cd $out
open_project $out
open_solution solution -flow_target vivado
set_top norm_integer
add_files src/norm_integer.cpp
add_files -tb src/test_norm.cpp
foreach f $files {add_files -tb $f}
set_part xc7z020clg400-1
create_clock -period 10 -name default
set_clock_uncertainty 1
config_compile -pipeline_loops 0
csim_design
csynth_design
cosim_design -rtl verilog -tool xsim
export_design -format ip_catalog -rtl verilog
