if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 1000000
puts [targets]
targets -set -filter {name =~ "DAP*"}
rst -system
after 2000
puts "AFTER_DAP_RESET [targets]"
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
