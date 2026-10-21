# Full packed detector experiment; preserves the verified V172 hardware.
set root [file normalize [file join [file dirname [info script]] ../..]]
set out [file normalize $::env(TILE_PACKED_DETECTOR_HLS)]
set vectors [file normalize $::env(TILE_PACKED_DETECTOR_VECTORS)]
if {[file exists $out]} {error "Fresh packed detector output required"}
file mkdir $out/src
set kernel $root/experimental/packed_mac_v173/texture_packed.cpp
if {[info exists ::env(TILE_PACKED_DETECTOR_SOURCE)]} {set kernel [file normalize $::env(TILE_PACKED_DETECTOR_SOURCE)]}
file copy $kernel $out/src/texture_integer.cpp
file copy $root/experimental/texture_v170/hls/test_integer.cpp $out/src/test_integer.cpp
foreach name {test_model.bin test_rgb.bin test_expected.bin test_fa_expected.bin test_fb_expected.bin} {file copy $vectors/$name $out/$name}
cd $out
open_project $out
open_solution solution -flow_target vivado
set_top texture_integer
add_files src/texture_integer.cpp
add_files -tb src/test_integer.cpp -cflags {-DTILE_TEST_WIDTH=79 -DTILE_TEST_HEIGHT=65 -DTILE_TEST_WORK_DEPTH=16384 -DTILE_TEST_INPUT_DEPTH=8192 -DTILE_TEST_RESULT_DEPTH=8192}
foreach name {test_model.bin test_rgb.bin test_expected.bin test_fa_expected.bin test_fb_expected.bin} {add_files -tb $name}
set_part xc7z020clg400-1
create_clock -period 10 -name default
set_clock_uncertainty 1
config_compile -pipeline_loops 0
csim_design
csynth_design
set f [open $out/solution/syn/report/texture_integer_csynth.xml r];set area [read $f];close $f
if {![regexp {<Resources>(.*?)</Resources>} $area _ resources] || ![regexp {<BRAM_18K>([0-9]+)</BRAM_18K>} $resources _ bram] || ![regexp {<DSP>([0-9]+)</DSP>} $resources _ dsp]} {error "Missing synthesized capacity report"}
if {$bram>276||$dsp>220} {error "Packed detector exceeds video board budget: BRAM18=$bram DSP=$dsp; RTL/export blocked"}
cosim_design -rtl verilog -tool xsim
export_design -format ip_catalog -rtl verilog
puts "PACKED_FULL_DETECTOR_HLS_FINISHED_NOT_BOARD_VALIDATION"
exit
