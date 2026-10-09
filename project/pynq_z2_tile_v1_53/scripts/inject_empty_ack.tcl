# Controlled diagnostic: publish one invalid future ACK into an EMPTY mailbox.
# No image, descriptor, slot ownership or CPU execution state is overwritten.
if {[llength $argv]!=2} {error "Need expected boot and proof JSON"}
lassign $argv boot output
set root [file normalize [file join [file dirname [info script]] ..]]
connect
after 500
targets -set -filter {name == "APU"}
loadhw -hw $root/pynq_z2_tile_v1_53.sdk/system.xsa
proc rd {a} {return [expr [lindex [mrd -value $a 1] 0]]}
proc words {a n} {set out {};foreach x [mrd -value $a $n] {lappend out [expr {$x+0}]};return $out}
if {[rd 0x10000000]!=0x54494c33 || [rd 0x10000004]!=0x11200 || [rd 0x10000008]!=$boot} {error "Wrong release or boot; injection refused"}
set before [words 0x10000000 24]
set head [lindex $before 4]
if {[lindex $before 5]!=$head || [lindex $before 6]!=0} {error "Queue not empty; injection refused"}
set requested [expr {($head+1)&0xffffffff}]
mwr 0x1000002c $requested
set deadline [expr {[clock milliseconds]+1500}]
while {1} {
 if {[rd 0x10000008]!=$boot} {error "Boot changed during injection"}
 if {[rd 0x1000005c]==[expr {([lindex $before 23]+1)&0xffffffff}]} {break}
 if {[clock milliseconds]>$deadline} {error "Rejected mailbox request was not consumed"}
 after 5
}
set after [words 0x10000000 24]
if {[lindex $after 4]!=$head || [lindex $after 5]!=$head || [lindex $after 6]!=0 || [lindex $after 11]!=$head} {error "Invalid ACK changed queue or remained latched"}
set f [open $output w]
puts $f "{\"passed\":true,\"requested\":$requested,\"before\":\[[join $before ,]\],\"after\":\[[join $after ,]\]}"
close $f
disconnect
exit
