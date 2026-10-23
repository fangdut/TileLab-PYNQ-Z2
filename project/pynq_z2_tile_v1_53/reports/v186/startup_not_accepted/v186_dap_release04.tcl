if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 1000000
puts [targets]
targets -set -filter {name =~ "DAP*"}
puts "CPU_RESET_CONTROL [mrd -force -value 0xf8000244 1]"
mwr -force 0xf8000008 0xdf0d
mwr -force 0xf8000244 0
mwr -force 0xf8000004 0x767b
after 1000
puts "AFTER_CPU_CLOCK_RELEASE [targets]"
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
