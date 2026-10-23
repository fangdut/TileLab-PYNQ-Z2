if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
puts "PREVIOUS_JTAG_CLOCK [jtag frequency]"
if {[jtag frequency 1000000] != 1000000} {error "Could not select 1MHz JTAG clock"}
puts "PROGRAM_JTAG_CLOCK [jtag frequency]"
set inventory [targets]
puts $inventory
if {![regexp {ARM Cortex-A9} $inventory]} {
 targets -set -filter {name == "xc7z020"}
 fpga -file {D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.bit}
 after 2000
 disconnect
 connect -url tcp:127.0.0.1:3121
 jtag targets -set 1
 if {[jtag frequency 1000000] != 1000000} {error "Could not select 1MHz JTAG clock"}
 puts [targets]
}
targets -set -filter {name =~ "ARM*#0"}
rst -system
after 1000
stop
source {D:/Vivado/TileLab_RealPhotos_20261020/v186_usb_restore17906/program/ps7_init.tcl}
ps7_init
fpga -file {D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.bit}
ps7_post_config
dow {D:/Vivado/TileLab_RealPhotos_20261020/v179_acceptance01/software.sdk/texture_transport/build/texture_transport.elf}
mwr 0x05f00000 [list 0 0 1350194707 0 0 0 0 0]
con
after 2000
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.xsa}
if {[expr [lindex [mrd -value 0x41200000 1] 0]] != 0x17000001} {error "Wrong PL build identity"}
set ready 0
for {set i 0} {$i<30} {incr i} {
 if {[expr [lindex [mrd -value 0x05f00000 1] 0]] == 0x17000001} {set ready 1;break}
 after 1000
}
if {!$ready} {error "Transport firmware did not start within PHY initialization deadline"}
puts "V170_VOLATILE_LOAD_PASSED"
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
