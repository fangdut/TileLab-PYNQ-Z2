if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 3000000
targets -set -filter {name =~ "ARM*#0"}
rst -processor
after 500
if {[catch {stop} why] && $why ne "Already stopped"} {error $why}
dow {D:/Vivado/TileLab_RealPhotos_20261020/v186_acceptance02/software.sdk/texture_transport/build/texture_transport.elf}
mwr 0x05f00000 [list 0 0 2980174417 0 0 0 0 0]
bpadd -addr 0x00117730 -type hw
bpadd -addr 0x00117734 -type hw
con
after 100
puts "DCACHE_TARGETS [targets]"
puts "DCACHE_PC [rrd pc]"
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
