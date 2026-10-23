if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 3000000
puts [targets]
targets -set -filter {name =~ "ARM*#0"}
puts "BEFORE [rrd pc]"
bpadd -addr 0x00117764 -type hw
puts "BREAKPOINTS [bplist]"
con
after 100
puts "AFTER_TARGETS [targets]"
if {[catch {stop} why] && $why ne "Already stopped"} {error $why}
puts "AFTER_PC [rrd pc]"
puts "AFTER_LR [rrd lr]"
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
