# Resume only a source-identical synthesis-only project, after other large jobs.
set out [file normalize $::env(TILE_PACKED_DETECTOR_HLS)]
set kernel [file normalize $::env(TILE_PACKED_DETECTOR_SOURCE)]
set f [open $kernel rb];set current [read $f];close $f
set f [open $out/src/texture_integer.cpp rb];set built [read $f];close $f
if {$current ne $built} {error "Source changed after synthesis"}
if {[file exists $out/solution/sim/report/texture_integer_cosim.rpt]} {error "Do not overwrite previous RTL evidence"}
set f [open $out/solution/csim/report/texture_integer_csim.log r];set proof [read $f];close $f
if {![string match *V170_COMPLETE_INTEGER_TWO_LAUNCH_PASS* $proof] || ![string match *CSim\ done\ with\ 0\ errors* $proof]} {error "Complete C simulation proof missing"}
set f [open $out/solution/syn/report/texture_integer_csynth.xml r];set area [read $f];close $f
if {![regexp {<Resources>(.*?)</Resources>} $area _ resources] || ![regexp {<BRAM_18K>([0-9]+)</BRAM_18K>} $resources _ bram] || ![regexp {<DSP>([0-9]+)</DSP>} $resources _ dsp]} {error "Capacity report missing"}
if {$bram>276||$dsp>220} {error "Video capacity gate failed"}
cd $out
open_project $out
open_solution solution
cosim_design -rtl verilog -tool xsim
export_design -format ip_catalog -rtl verilog
puts "PACKED_FULL_DETECTOR_HLS_FINISHED_NOT_BOARD_VALIDATION"
exit
