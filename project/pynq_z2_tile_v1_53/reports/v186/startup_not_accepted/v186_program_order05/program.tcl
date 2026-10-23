if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
if {[jtag frequency 3000000] != 3000000} {error "Stable 3MHz JTAG clock not selected"}
puts "CONFIGURE_FIRST_BEGIN"
puts [targets]
targets -set -filter {name =~ "ARM*#0"}
rst -system
after 1000
stop
targets -set -filter {name == "xc7z020"}
fpga -file {D:/Vivado/TileLab_RealPhotos_20261020/v186_hw01/system.bit}
puts "PL_CONFIGURATION_COMPLETE"
after 2000
disconnect
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 3000000
puts [targets]
targets -set -filter {name =~ "ARM*#0"}
if {[catch {stop} why] && $why ne "Already stopped"} {error $why}
source {D:/Vivado/TileLab_RealPhotos_20261020/v186_program_order05/ps7_init.tcl}
ps7_init
ps7_post_config
puts "PS_DDR_SETUP_COMPLETE"
dow {D:/Vivado/TileLab_RealPhotos_20261020/v186_acceptance02/software.sdk/texture_transport/build/texture_transport.elf}
mwr 0x05f00000 [list 0 0 3399081862 0 0 0 0 0]
con
after 2000
# Only retry debug enumeration after startup, never FPGA/{D:/Vivado/TileLab_RealPhotos_20261020/v186_acceptance02/software.sdk/texture_transport/build/texture_transport.elf} programming.
set startup_targets {}
for {set attempt 0} {$attempt<10} {incr attempt} {
 set startup_targets [targets]
 if {[regexp {ARM Cortex-A9} $startup_targets]} {break}
 puts "WAITING_FOR_STARTUP_DEBUG_TARGET $attempt $startup_targets"
 after 1000
 disconnect
 connect -url tcp:127.0.0.1:3121
 jtag targets -set 1
 if {[jtag frequency 3000000] != 3000000} {error "Stable 3MHz JTAG clock not selected"}
}
if {![regexp {ARM Cortex-A9} $startup_targets]} {error "ARM debug target did not recover after startup"}
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v186_hw01/system.xsa}
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
