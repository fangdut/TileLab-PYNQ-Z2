set root [file normalize [file join [file dirname [info script]] ../..]]
foreach key {TILE_NATIVE_HLS TILE_NATIVE_VECTORS} {if {![info exists ::env($key)]} {error "Set $key"}}
set out [file normalize $::env(TILE_NATIVE_HLS)]
if {[file exists $out]} {error "Fresh HLS directory required"}
file mkdir $out/src
foreach f {native_line.cpp test_native.cpp} {file copy $root/experimental/native_line_v196/$f $out/src/}
foreach f {pixels.bin expected.bin} {file copy $::env(TILE_NATIVE_VECTORS)/$f $out/}
cd $out
open_project $out
open_solution solution -flow_target vivado
set_top native_line
add_files src/native_line.cpp
add_files -tb src/test_native.cpp
foreach f {pixels.bin expected.bin} {add_files -tb $f}
set_part xc7z020clg400-1
create_clock -period 10 -name default
set_clock_uncertainty 1
config_compile -pipeline_loops 0
csim_design
csynth_design
cosim_design -rtl verilog -tool xsim
export_design -format ip_catalog -rtl verilog
