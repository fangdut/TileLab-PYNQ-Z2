if {[catch {
connect -url tcp:127.0.0.1:3121
puts "JTAG_CABLES [jtag targets]"
jtag targets -set 1
puts "SUPPORTED_JTAG_FREQUENCIES [jtag frequency -list]"
puts "SELECTED_JTAG_FREQUENCY [jtag frequency 1000000]"
puts [targets]
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
