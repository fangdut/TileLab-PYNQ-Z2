if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 1000000
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v199_hardware_binding01/system.xsa}
set old [expr [lindex [mrd -value 0xf8000258 1] 0]]
puts [format "RESET_REASON_BEFORE_CLEAR 0x%08x" $old]
mwr 0xf8000008 0xdf0d
mwr 0xf8000258 [expr {$old & ~0x007f0000}]
mwr 0xf8000004 0x767b
set cleared [expr [lindex [mrd -value 0xf8000258 1] 0]]
puts [format "RESET_REASON_BASELINE 0x%08x" $cleared]
if {($cleared & 0x007f0000) != 0} {error "Reset reason not cleared"}
puts "BOOT_AND_STATUS [mrd -value 0x05f00000 8]"
disconnect
} why]} {puts stderr $why;exit 1}
exit 0
