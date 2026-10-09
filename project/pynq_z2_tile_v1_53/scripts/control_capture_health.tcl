# V1.19 diagnostic only. No automatic recovery and no descriptor/slot writes.
# AMD PG021: clearing S2MM RS can truncate active packets. Restore a clean
# release after the halt case; do not resume the old partially received ring.
if {[llength $argv]!=4} {error "Need expected boot, operation, expected event, proof JSON"}
lassign $argv boot operation event output
if {$operation ni {pause_input resume_input halt_dma}} {error "Unknown diagnostic operation"}
set root [file normalize [file join [file dirname [info script]] ..]]
connect
after 500
targets -set -filter {name == "APU"}
loadhw -hw $root/pynq_z2_tile_v1_53.sdk/system.xsa
proc rd {a} {return [expr [lindex [mrd -value $a 1] 0]]}
proc words {a n} {set out {};foreach x [mrd -value $a $n] {lappend out [expr {$x+0}]};return $out}
if {[rd 0x10000000]!=0x54494c33 || [rd 0x10000004]!=0x11300 || [rd 0x10000008]!=$boot} {error "Wrong firmware/boot; no writes performed"}
if {$operation ne "resume_input" && ([rd 0x10000010]!=(($event-1)&0xffffffff) || [rd 0x10000018]!=1)} {error "Expected exactly the pinned evidence event"}
set before [words 0x10000000 72]
set cr [rd 0x40400030]
set sr [rd 0x40400034]
if {$operation eq "halt_dma"} {mwr 0x40400030 [expr {$cr&0xfffffffe}]} else {mwr 0x41290008 [expr {$operation eq "pause_input"?0:2}]}
after 650
if {[rd 0x10000008]!=$boot} {error "Boot changed during diagnostic"}
set after [words 0x10000000 72]
set f [open $output w]
puts $f "{\"operation\":\"$operation\",\"boot_id\":$boot,\"event\":$event,\"before_control\":$cr,\"before_status\":$sr,\"after_control\":[rd 0x40400030],\"after_status\":[rd 0x40400034],\"before\":\[[join $before ,]\],\"after\":\[[join $after ,]\]}"
close $f
disconnect
exit
