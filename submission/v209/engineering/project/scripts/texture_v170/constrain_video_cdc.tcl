# Only asynchronous level inputs to the FIRST flop of a documented 3-FF
# synchronizer. Keep all downstream stages and all algorithm paths timed.
# No blanket asynchronous clock groups: XPM FIFO Gray-bus max-delay constraints
# must remain effective.
foreach pattern {
 {.*pipeline/inst/lock_sync_reg\[0\]$}
 {.*pipeline/inst/capture/producer/request_sync_reg\[0\]$}
 {.*border/inst/alarm_sync_reg\[0\]$}
 {.*border/inst/valid_sync_reg\[0\]$}
} {
 set cells [get_cells -hier -regexp $pattern]
 if {[llength $cells]!=1} {error "Expected exactly one CDC first stage: $pattern, got $cells"}
 set cell [lindex $cells 0]
 if {![get_property ASYNC_REG $cell]} {error "CDC stage lacks ASYNC_REG: $cell"}
 set q [get_pins $cell/Q]
 set sinks [get_pins -leaf -of_objects [get_nets -of_objects $q] -filter {DIRECTION == IN}]
 if {[llength $sinks]!=1} {error "CDC first stage must feed only its next synchronizer stage: $cell $sinks"}
 set next [get_cells -of_objects $sinks]
 if {![get_property ASYNC_REG $next]} {error "CDC first-stage output is used outside synchronizer: $cell"}
 puts "CDC_FIRST_STAGE_ONLY $cell/D -> $sinks"
 set_false_path -to [get_pins $cell/D]
}
# The reset request is the OR of two active reset requests; deassertion is
# filtered through four PRE-initialized flops in PixelClk. Only asynchronous
# PRE recovery/removal endpoints are excluded, never data or later-stage D.
set reset_cells [get_cells -hier -regexp {.*pipeline/inst/capture/reset_pipe_reg\[[0-3]\]$}]
if {[llength $reset_cells]!=4} {error "Expected four-stage asynchronous reset release bridge"}
set reset_nets {}
for {set i 0} {$i<4} {incr i} {
 set cell [lindex [get_cells -hier -regexp [format {.*pipeline/inst/capture/reset_pipe_reg\[%d\]$} $i]] 0]
 if {![get_property ASYNC_REG $cell]} {error "Reset release stage lacks ASYNC_REG"}
 set pin [get_pins $cell/PRE]
 if {[llength $pin]!=1} {error "Expected asynchronous PRE pin on reset bridge"}
 lappend reset_nets [get_nets -of_objects $pin]
 if {$i<3} {
  set sinks [get_pins -leaf -of_objects [get_nets -of_objects [get_pins $cell/Q]] -filter {DIRECTION == IN}]
  if {[llength $sinks]!=1 || ![regexp [format {reset_pipe_reg\[%d\]/D$} [expr {$i+1}]] $sinks]} {error "Reset release chain is not isolated/contiguous"}
 }
 puts "ASYNC_RESET_RELEASE_PRE_ONLY $pin"
 set_false_path -to $pin
}
if {[llength [lsort -unique $reset_nets]]!=1} {error "Reset release stages have different asynchronous requests"}
set first [lindex [get_cells -hier -regexp {.*pipeline/inst/capture/reset_pipe_reg\[0\]$}] 0]
set drivers [get_pins -leaf -of_objects [get_nets -of_objects [get_pins $first/D]] -filter {DIRECTION == OUT}]
if {[llength $drivers]!=1 || [get_property REF_NAME [get_cells -of_objects $drivers]] ne "GND"} {error "Reset release stage zero must shift in constant zero"}
set ::tile_video_cdc_applied 1
