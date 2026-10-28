if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 1000000
targets
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v199_hardware_binding01/system.xsa}
foreach addr {0xf8000200 0xf8000204 0xf8000244 0xf8000258 0xf8000600 0xf8007000 0xe000b000 0x05f00000} {
 if {[catch {mrd -value $addr 8} value]} {puts "READ_ERROR $addr $value"} else {puts "READ $addr $value"}
}
targets -set -filter {name =~ "ARM*#0"}
if {[catch {stop} value]} {puts "STOP_ERROR $value"} else {
 foreach reg {r0 r1 r2 r3 sp lr pc cpsr} {puts "$reg [rrd $reg]"}
 con
}
disconnect
} why]} {puts stderr $why;exit 1}
exit 0
