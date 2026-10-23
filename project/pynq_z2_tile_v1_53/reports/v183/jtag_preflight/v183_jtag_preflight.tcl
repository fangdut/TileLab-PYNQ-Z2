if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
puts "JTAG_FREQUENCY [jtag frequency 3000000]"
puts "TARGETS_START"
puts [targets]
targets -set -filter {name == "APU"}
puts "CURRENT_BOOT_MAILBOX [mrd -value 0x05f00000 8]"
puts "CURRENT_PL_ID [mrd -value 0x41200000 1]"
puts "TARGETS_FINAL"
puts [targets]
disconnect
} why]} {puts stderr $why;exit 1}
exit 0
