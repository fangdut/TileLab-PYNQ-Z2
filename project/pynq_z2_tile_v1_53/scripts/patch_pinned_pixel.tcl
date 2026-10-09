# Test-only reversible single word mutation of the current pinned event.
if {[llength $argv]!=6} {error "Expected boot event slot pixel-index old new"}
lassign $argv boot event slot index old new
proc rd {a} {return [expr [lindex [mrd -value $a 1] 0]]}
if {$slot<0x10100000 || $slot>=0x1c100000 || ($slot-0x10100000)%0x400000 || $index<0 || $index>=921600} {error "Not an in-range owned frame pixel"}
connect
try {
 jtag targets -open -filter {name =~ "Xilinx TUL*"}
 jtag targets -set -filter {name =~ "Xilinx TUL*"}
 jtag frequency 1000000
 targets -set -filter {name == "APU"}
 if {[rd 0x10000000]!=0x54494c33 || [rd 0x10000004]!=0x11a00 || [rd 0x10000008]!=$boot} {error "Board identity mismatch"}
 if {[rd 0x10000018]<1 || (([rd 0x10000010]+1)&0xffffffff)!=$event} {error "Pinned event identity changed"}
 set pos [rd 0x10000100]
 if {$pos>=12} {error "Invalid queue position"}
 set desc [expr {0x10001000+$pos*160}]
 if {[rd $desc]!=$event || [rd [expr {$desc+4}]]!=$slot} {error "Queue does not own this slot"}
 set address [expr {$slot+4*$index}]
 if {[rd $address]!=$old} {error "Original word differs; refusing write"}
 mwr $address $new
 if {[rd $address]!=$new} {error "Pixel write not observed"}
 puts "PASS pinned event pixel changed from $old to $new without releasing event"
} finally {disconnect}
exit
