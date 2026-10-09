# Dedicated SGI diagnostics; no flash writes and no application image capture.
set root [file normalize [file join [file dirname [info script]] ..]]
set ws $root/pynq_z2_tile_v1_53.sdk
if {[llength $argv]!=5} {error "Need variant, result address, expected address, observed address and output JSON"}
lassign $argv variant address expected observed output
if {$variant ni {baseline candidate}} {error "Unknown diagnostic variant"}
foreach value [list $address $expected $observed] {
 if {![string is integer -strict $value] || $value<0x100000 || $value>=0x10000000} {error "Result address outside linked application DDR"}
}
connect
after 1500
jtag targets -open -filter {name =~ "Xilinx TUL*"}
jtag targets -set -filter {name =~ "Xilinx TUL*"}
jtag frequency 1000000
targets -set -filter {name =~ "ARM*#0"}
rst -system
after 500
stop
source $ws/hdmi_ethernet/_ide/psinit/ps7_init.tcl
ps7_init
ps7_post_config
dow $root/reports/v132/irq_context/$variant/diagnostic.elf
con
targets -set -filter {name == "APU"}
loadhw -hw $ws/system.xsa
set done 0
for {set i 0} {$i<100} {incr i} {
 after 50
 set state [expr [lindex [mrd -value [expr {$address+4}] 1] 0]]
 if {$state==2 || $state>=0x80000000} {set done 1;break}
}
if {!$done} {error "Diagnostic did not finish within five-second poll window"}
targets -set -filter {name =~ "ARM*#0"}
stop
targets -set -filter {name == "APU"}
proc numbers {addr count} {
 set result {}
 foreach value [mrd -value $addr $count] {lappend result [expr {$value+0}]}
 return [join $result ,]
}
set f [open $output w]
puts $f "{\"variant\":\"$variant\",\"result\":\[[numbers $address 32]\],\"first_expected\":\[[numbers $expected 64]\],\"first_observed\":\[[numbers $observed 64]\]}"
close $f
puts "Read completed actual GIC software-interrupt diagnostic: $variant state=$state"
disconnect
exit
