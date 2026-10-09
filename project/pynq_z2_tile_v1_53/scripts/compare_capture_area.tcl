set root [file normalize [file join [file dirname [info script]] ..]]
set_param general.maxThreads 2
foreach revision {v114 v115} {
 create_project -in_memory -part xc7z020clg400-1
 set_property XPM_LIBRARIES {XPM_CDC} [current_project]
 read_verilog $root/rtl/product_tracker.v
 if {$revision eq "v114"} {
  read_verilog $root/sim/frame_capture_v114_reference.v
  set top frame_capture_v114
 } else {
  read_verilog $root/rtl/frame_capture_sg.v
  set top frame_capture
 }
 synth_design -mode out_of_context -top $top -part xc7z020clg400-1
 report_utilization -file $root/reports/v132/capture_${revision}_utilization.rpt
 write_checkpoint -force $root/reports/v132/capture_${revision}_synth.dcp
 close_project
}
