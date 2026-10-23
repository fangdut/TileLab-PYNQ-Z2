if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
puts "previous_jtag_clock [jtag frequency]"
if {[jtag frequency 1000000] != 1000000} {error "Could not select 1MHz JTAG clock"}
puts "program_jtag_clock [jtag frequency]"
set inventory [targets]
puts $inventory
if {![regexp {ARM Cortex-A9} $inventory]} {
 targets -set -filter {name == "xc7z020"}
 fpga -file {D:/Vivado/TileLab_RealPhotos_20261020/v186_hw01/system.bit}
 after 2000
 disconnect
 connect -url tcp:127.0.0.1:3121
 jtag targets -set 1
 if {[jtag frequency 1000000] != 1000000} {error "Could not select 1MHz JTAG clock"}
 puts "program_jtag_clock [jtag frequency]"
 puts [targets]
}
targets -set -filter {name =~ "ARM*#0"}
puts "stage_reset_begin"
rst -system
after 1000
stop
source {D:/Vivado/TileLab_RealPhotos_20261020/v186_acceptance04/program/ps7_init.tcl}
puts "stage_ps_init_begin"
ps7_init
puts "stage_bit_download_begin"
fpga -file {D:/Vivado/TileLab_RealPhotos_20261020/v186_hw01/system.bit}
puts "stage_bit_download_done"
ps7_post_config
puts "stage_elf_download_begin"
dow {D:/Vivado/TileLab_RealPhotos_20261020/v186_acceptance04/software.sdk/texture_transport/build/texture_transport.elf}
puts "stage_elf_download_done"
mwr 0x05f00000 [list 0 0 2814040743 0 0 0 0 0]
con
puts "stage_run_done"
after 2000
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v186_hw01/system.xsa}
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
