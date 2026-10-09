# Volatile JTAG programming only. Select JTAG boot mode with board power OFF first.
set ws [file dirname [file normalize [info script]]]
# Default matches a PC direct cable with its automatic 169.254/16 address.
# Pass "dhcp" for a router, or an explicit 169.254.x.y board address.
set address "169.254.200.10"
if {[llength $argv]>0} {set address [lindex $argv 0]}
set ipvalue 0
if {$address ne "dhcp"} {
 if {![regexp {^([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})$} $address -> a b c d]} {error "Use dhcp or a private/direct-link IPv4 address"}
 foreach part {a b c d} {scan [set $part] %d $part;if {[set $part]>255} {error "Invalid IPv4 octet"}}
 if {!(($a==169 && $b==254 && $c>0 && $c<255) || $a==10 || ($a==172 && $b>=16 && $b<=31) || ($a==192 && $b==168)) || $d==0 || $d==255} {error "Use a usable RFC1918 or link-local host address"}
 set ipvalue [expr {($a<<24)|($b<<16)|($c<<8)|$d}]
}
set timing [file join $ws .. reports timing_summary.rpt]
if {![file exists $timing]} {error "Timing report missing; complete implementation before programming"}
set f [open $timing r];set report [read $f];close $f
if {![string match {*All user specified timing constraints are met*} $report]} {error "Timing has not passed. Refusing to program this build."}
connect
after 3000
jtag targets -open -filter {name =~ "Xilinx TUL*"}
jtag targets -set -filter {name =~ "Xilinx TUL*"}
puts "Programming JTAG at [jtag frequency 1000000] Hz"
after 1000
set cpus [targets -target-properties -filter {name =~ "ARM*#0"}]
if {[llength $cpus] != 1} {puts [targets];error "Expected one Cortex-A9 #0. Check board power, PROG-UART data cable and JTAG driver."}
targets -set -filter {name =~ "ARM*#0"}
rst -system
after 1000
stop
fpga -file $ws/system.bit
source $ws/ps7_init.tcl
ps7_init
ps7_post_config
dow $ws/hdmi_ethernet/build/hdmi_ethernet.elf
set py [file join $::env(USERPROFILE) .cache codex-runtimes codex-primary-runtime dependencies python python.exe]
if {![file exists $py]} {set py python}
set boot [string trim [exec $py $ws/reserve_boot_id.py]]
mwr 0x100000f0 [list $boot [expr {(~$boot)&0xffffffff}]]
mwr 0x10000400 [list 0x544e4554 $ipvalue 0 0 [expr {(~$ipvalue)&0xffffffff}]]
con
after 300
targets -set -filter {name == "APU"}
if {[expr [lindex [mrd -value 0x10000000 1] 0]]!=0x54494c33 || [expr [lindex [mrd -value 0x10000008 1] 0]]!=$boot} {error "ARM application did not publish the reserved boot identity"}
# loadhw can re-extract the BIT and change its mtime without changing contents.
# Record content digests only after actual FPGA/ELF programming succeeds.
exec $py $ws/record_programming.py ethernet $address
puts "Programmed volatile PL configuration and ARM application. Open UART at 115200 8N1."
puts "Ethernet mode/address: $address (TCP 9133)"
disconnect
exit

