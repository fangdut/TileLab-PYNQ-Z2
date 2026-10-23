if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
puts "JTAG_CLOCK [jtag frequency 1000000]"
puts [targets]
targets -set -filter {name == "APU"}
foreach address {0xf8000258 0xf8000170 0x05f00000 0x07000000 0x43c10000 0x41200000} {
 puts "READ_ADDRESS $address"
 puts [mrd $address 16]
}
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
