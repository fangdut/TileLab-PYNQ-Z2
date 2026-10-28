if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 1000000
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v199_hardware_binding01/system.xsa}
set old [expr [lindex [mrd -value 0xf8000170 1] 0]]
if {($old & 0x03f03f30) != 0x00200500} {error "Not baseline FCLK0 divider5x2"}
set ctrl [expr [lindex [mrd -value 0x43c10000 1] 0]]
if {$ctrl & 0x81} {error "PL must be idle"}
puts [format "BASELINE_FCLK0 0x%08x" $old]
mwr 0xf8000008 0xdf0d
mwr 0xf8000170 [expr {($old & ~0x3f00) | 0xa00}]
mwr 0xf8000004 0x767b
set changed [expr [lindex [mrd -value 0xf8000170 1] 0]]
puts [format "LOWER_FCLK0 0x%08x" $changed]
if {($changed & 0x03f03f30) != 0x00200a00} {error "FCLK0 divider change failed"}
puts "PL_ID [mrd -value 0x41200000 1]"
puts "ARM_CLK [mrd -value 0xf8000120 1]"
puts "LOWER_FCLK0_DIAGNOSTIC_NOT_CHANGED_BITSTREAM_METADATA"
disconnect
} why]} {puts stderr $why;exit 1}
exit 0
