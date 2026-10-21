set root [file normalize [file dirname [info script]]]
set out [file normalize $::env(TILE_PACKED_HLS)]
if {[file exists $out]} {error "Fresh packed prototype directory required"}
file mkdir $out/src
foreach name {packed_pair.cpp test_packed_pair.cpp} {file copy $root/$name $out/src/$name}
cd $out
open_project $out
open_solution solution -flow_target vivado
set_top packed_pair
add_files src/packed_pair.cpp
add_files -tb src/test_packed_pair.cpp
set_part xc7z020clg400-1
create_clock -period 10
csim_design
csynth_design
cosim_design -rtl verilog -trace_level none
export_design -format ip_catalog
puts "ISOLATED_PACKED_HLS_BUILD_FINISHED_NOT_SYSTEM_VALIDATION"
exit
