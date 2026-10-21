set out [file normalize $::env(TILE_TEXTURE_HW)]
set_param general.maxThreads 2
open_checkpoint $out/video_accepted.dcp
report_bus_skew -file $out/bus_skew.rpt
report_exceptions -file $out/video_exceptions.rpt
set f [open $out/bus_skew.rpt r];set proof [read $f];close $f
if {[regexp -nocase {VIOLATED} $proof]} {error "Asynchronous FIFO bus skew failed"}
puts "VIDEO_FIFO_BUS_SKEW_PASSED"
exit
