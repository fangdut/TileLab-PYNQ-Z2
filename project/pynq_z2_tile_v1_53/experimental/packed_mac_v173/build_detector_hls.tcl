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
set f [open $kernel r];set source_text [read $f];close $f
foreach {port vector bytes} {model test_model.bin 8 rgb test_rgb.bin 4 result test_expected.bin 4} {
 if {![regexp [format {port=%s[^\r\n]*depth=([0-9]+)} $port] $source_text _ depth]} {error "Missing constant simulation depth for $port"}
 if {[file size $out/$vector]>$depth*$bytes} {error "Fixture exceeds declared $port simulation depth; select a matching fixture before synthesis"}
}
if {![regexp {port=work[^\r\n]*depth=([0-9]+)} $source_text _ work_depth]} {error "Missing work simulation depth"}
set f [open $out/test_model.bin rb];set header [read $f 80];close $f
if {[string length $header]!=80} {error "Truncated fixture model header"}
binary scan $header iu* model_header
if {[lindex $model_header 16]>$work_depth*16} {error "Fixture exceeds declared work simulation depth"}
cd $out
open_project $out
open_solution solution -flow_target vivado
set_top texture_integer
add_files $out/src/texture_integer.cpp
set tb_flags {-DTILE_TEST_WIDTH=79 -DTILE_TEST_HEIGHT=65 -DTILE_TEST_WORK_DEPTH=16384 -DTILE_TEST_INPUT_DEPTH=8192 -DTILE_TEST_RESULT_DEPTH=8192}
if {[info exists ::env(TILE_PACKED_SMALL_FIXTURE)]} {set tb_flags {}}
add_files -tb $out/src/test_integer.cpp -cflags $tb_flags
foreach name {test_model.bin test_rgb.bin test_expected.bin test_fa_expected.bin test_fb_expected.bin} {add_files -tb $out/$name}
set_part xc7z020clg400-1
create_clock -period 10 -name default
set_clock_uncertainty 1
config_compile -pipeline_loops 0
csim_design
csynth_design
set f [open $out/solution/syn/report/texture_integer_csynth.xml r];set area [read $f];close $f
if {![regexp {<Resources>(.*?)</Resources>} $area _ resources] || ![regexp {<BRAM_18K>([0-9]+)</BRAM_18K>} $resources _ bram] || ![regexp {<DSP>([0-9]+)</DSP>} $resources _ dsp]} {error "Missing synthesized capacity report"}
if {$bram>276||$dsp>220} {error "Packed detector exceeds video board budget: BRAM18=$bram DSP=$dsp; RTL/export blocked"}
if {[info exists ::env(TILE_PACKED_SYNTH_ONLY)]} {
 puts "PACKED_FULL_DETECTOR_SYNTHESIS_ONLY_RTL_AND_BOARD_PENDING"
 close_project
 exit
}
cosim_design -rtl verilog -tool xsim
export_design -format ip_catalog -rtl verilog
puts "PACKED_FULL_DETECTOR_HLS_FINISHED_NOT_BOARD_VALIDATION"
exit
