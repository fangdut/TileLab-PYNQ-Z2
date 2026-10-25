if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
puts "PREVIOUS_JTAG_CLOCK [jtag frequency]"
if {[jtag frequency 1000000] != 1000000} {error "JTAG clock mismatch"}
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.xsa}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != 1667821003} {error "Boot changed; cannot reuse numerical validation"}
puts "PREFLIGHT_REGISTERS [mrd -value 0x43c20000 14]"
mwr 0x43c20000 0
set drained 0
for {set i 0} {$i<100} {incr i} {
 if {!([expr [lindex [mrd -value 0x43c20004 1] 0]] & 1)} {set drained 1;break}
 after 100
}
if {!$drained} {error "Previous video did not drain"}
puts "SAME_BOOT_DRAIN_PASS"
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
