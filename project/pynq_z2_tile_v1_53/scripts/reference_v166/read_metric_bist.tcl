# Read actual VIO hardware result, then explicitly restart twice.
foreach name {TILE_METRIC_BIST_OUT TILE_METRIC_BIST_READ_OUT} {if {![info exists ::env($name)]} {error "Set $name"}}
set out $::env(TILE_METRIC_BIST_READ_OUT)
if {[file exists $out]} {error "Never overwrite board evidence"}
file mkdir $out
open_hw_manager
connect_hw_server -url localhost:3121
open_hw_target
set device [get_hw_devices xc7z020*]
if {[llength $device]!=1} {error "Expected exactly one xc7z020"}
current_hw_device $device
set_property PROBES.FILE $::env(TILE_METRIC_BIST_OUT)/metric_bist.ltx $device
refresh_hw_device $device
set vio [get_hw_vios -of_objects $device]
if {[llength $vio]!=1} {error "Expected one metric self-test VIO"}
set input [get_hw_probes -of_objects $vio -filter {TYPE == vio_input}]
set output [get_hw_probes -of_objects $vio -filter {TYPE == vio_output}]
if {[llength $input]!=1 || [llength $output]!=1} {error "Unexpected hardware probes"}
set f [open $out/readback.txt w]
for {set trial 0} {$trial<3} {incr trial} {
 if {$trial>0} {
  set_property OUTPUT_VALUE 1 $output;commit_hw_vio $vio;after 20
  set_property OUTPUT_VALUE 0 $output;commit_hw_vio $vio;after 100
 }
 refresh_hw_vio $vio
 set value [get_property INPUT_VALUE $input]
 puts $f "TRIAL $trial $value";flush $f
 puts "TILELAB_METRIC_BIST_TRIAL $trial $value"
 set n [expr 0x$value]
 if {($n>>48)!=0x166b || (($n>>47)&1)!=1 || (($n>>45)&3)!=0 || (($n>>33)&4095)!=2048 || (($n>>21)&4095)!=2048 || (($n>>8)&8191)!=0} {close $f;error "Hardware arithmetic BIST failed"}
}
puts $f "PASS three actual hardware runs,2048 windows each,zero mismatches";close $f
close_hw_manager
