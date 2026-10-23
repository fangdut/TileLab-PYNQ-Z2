if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 3000000
puts [targets]
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v186_hw01/system.xsa}
puts "RESET_REASON [mrd -value 0xf8000258 1]"
puts "SLCR_CLOCK [mrd -value 0xf8000170 1]"
puts "SYSTEM_WATCHDOG [mrd -value 0xf8005000 4]"
puts "CPU0_WATCHDOG [mrd -value 0xf8f00620 4]"
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
