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
source {D:/Vivado/TileLab_RealPhotos_20261020/v179_acceptance01/program/ps7_init.tcl}
ps7_init
ps7_post_config
puts "PS_DDR_SETUP_COMPLETE"
dow {D:/Vivado/TileLab_RealPhotos_20261020/v186_acceptance02/software.sdk/texture_transport/build/texture_transport.elf}
mwr 0x05f00000 [list 0 0 1041888739 0 0 0 0 0]
bpadd -addr 0x00117730 -type hw
bpadd -addr 0x00117734 -type hw
con
after 100
puts "DCACHE_TARGETS [targets]"
puts "DCACHE_PC [rrd pc]"
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
