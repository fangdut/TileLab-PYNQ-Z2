if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 3000000
targets -set -filter {name =~ "ARM*#0"}
if {[catch {stop} why] && $why ne "Already stopped"} {error $why}
dow {D:/Vivado/TileLab_RealPhotos_20261020/v186_acceptance02/software.sdk/texture_transport/build/texture_transport.elf}
mwr 0x05f00000 [list 0 0 1937161011 0 0 0 0 0]
puts "DOWNLOADED_TARGETS [targets]"
puts "ENTRY [rrd pc]"
for {set i 0} {$i<32} {incr i} {
 stp
 after 10
 puts "STEP $i [rrd pc]"
}
puts "BOOT_STEPS_COMPLETE"
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
