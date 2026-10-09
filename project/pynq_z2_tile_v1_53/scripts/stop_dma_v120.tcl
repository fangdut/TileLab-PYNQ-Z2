# Guarded fault injection into the release firmware. No queue/slot/CPU reset.
if {[llength $argv]!=4} {error "Need expected boot, event, prior attempts, proof JSON"}
lassign $argv boot event attempts output
if {$attempts<0 || $attempts>3} {error "Invalid attempt number"}
set root [file normalize [file join [file dirname [info script]] ..]]
connect
after 300
targets -set -filter {name == "APU"}
loadhw -hw $root/pynq_z2_tile_v1_53.sdk/system.xsa
proc rd {a} {return [expr [lindex [mrd -value $a 1] 0]]}
proc words {a n} {set out {};foreach x [mrd -value $a $n] {lappend out [expr {$x+0}]};return $out}
if {[rd 0x10000000]!=0x54494c33 || [rd 0x10000004]!=0x11400 || [rd 0x10000008]!=$boot} {error "Wrong firmware/boot; no write"}
set before [words 0x10000000 86]
if {[lindex $before 4]!=(($event-1)&0xffffffff) || [lindex $before 6]!=1 || [lindex $before 72]!=0x52454331 || [lindex $before 73]!=0 || [lindex $before 74]!=$attempts} {error "Wrong pinned event or recovery state; no write"}
set control [rd 0x40400030]
set started [clock milliseconds]
mwr 0x40400030 [expr {$control&0xfffffffe}]
set observations {}
set target_attempt [expr {$attempts<3?$attempts+1:3}]
set deadline [expr {$started+8000}]
while {1} {
 set current [words 0x10000000 86]
 if {[lindex $current 2]!=$boot} {error "Boot changed during fault test"}
 lappend observations "{\"elapsed_ms\":[expr {[clock milliseconds]-$started}],\"state\":[lindex $current 73],\"attempts\":[lindex $current 74],\"successes\":[lindex $current 75],\"reason\":[lindex $current 77]}"
 if {[lindex $current 74]==$target_attempt && ([lindex $current 73]==3 || ([lindex $current 73]==0 && [lindex $current 75]==$target_attempt))} {break}
 if {[clock milliseconds]>$deadline} {error "Recovery did not reach a terminal state within 8 seconds"}
 after 10
}
set f [open $output w]
puts $f "{\"boot_id\":$boot,\"event\":$event,\"prior_attempts\":$attempts,\"before_control\":$control,\"after_control\":[rd 0x40400030],\"after_status\":[rd 0x40400034],\"before\":\[[join $before ,]\],\"after\":\[[join $current ,]\],\"observations\":\[[join $observations ,]\]}"
close $f
disconnect
exit
