if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
puts "PREVIOUS_JTAG_CLOCK [jtag frequency]"
puts "PROGRAM_JTAG_CLOCK [jtag frequency 1000000]"
set inventory [targets]
puts $inventory
if {![regexp {ARM Cortex-A9} $inventory]} {
 targets -set -filter {name == "xc7z020"}
 fpga -file {D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.bit}
 after 2000
 disconnect
 connect -url tcp:127.0.0.1:3121
jtag targets -set 1
puts "PREVIOUS_JTAG_CLOCK [jtag frequency]"
puts "PROGRAM_JTAG_CLOCK [jtag frequency 1000000]"
 puts [targets]
}
targets -set -filter {name =~ "ARM*#0"}

puts "STAGE_RESET_BEGIN"
rst -system
puts "STAGE_RESET_DONE"

after 1000
puts "STAGE_STOP_BEGIN"

stop

puts "STAGE_STOP_DONE"
source {D:/Vivado/TileLab_RealPhotos_20261020/v186_windows_reboot_restore17909/program/ps7_init.tcl}
puts "STAGE_PS_{D:/Vivado/TileLab_RealPhotos_20261020/v186_windows_reboot_restore17909/program/ps7_init.tcl}_BEGIN"

ps7_init

puts "STAGE_PS_{D:/Vivado/TileLab_RealPhotos_20261020/v186_windows_reboot_restore17909/program/ps7_init.tcl}_DONE"
puts "STAGE_{D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.bit}_DOWNLOAD_BEGIN"

fpga -file {D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.bit}

puts "STAGE_{D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.bit}_DOWNLOAD_DONE"
puts "STAGE_POST_CONFIG_BEGIN"

ps7_post_config

puts "STAGE_POST_CONFIG_DONE"
puts "STAGE_{D:/Vivado/TileLab_RealPhotos_20261020/v179_acceptance01/software.sdk/texture_transport/build/texture_transport.elf}_DOWNLOAD_BEGIN"

dow {D:/Vivado/TileLab_RealPhotos_20261020/v179_acceptance01/software.sdk/texture_transport/build/texture_transport.elf}

puts "STAGE_{D:/Vivado/TileLab_RealPhotos_20261020/v179_acceptance01/software.sdk/texture_transport/build/texture_transport.elf}_DOWNLOAD_DONE"
mwr 0x05f00000 [list 0 0 4084396836 0 0 0 0 0]
puts "STAGE_RUN_BEGIN"

con

puts "STAGE_RUN_DONE"
after 2000
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.xsa}
if {[expr [lindex [mrd -value 0x41200000 1] 0]] != 0x17000001} {error "Wrong PL build identity"}
set ready 0
for {set i 0} {$i<30} {incr i} {
 if {[expr [lindex [mrd -value 0x05f00000 1] 0]] == 0x17000001} {set ready 1;break}
 after 1000
}
if {!$ready} {error "Transport firmware did not start within PHY initialization deadline"}
puts "V170_VOLATILE_LOAD_PASSED"
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
