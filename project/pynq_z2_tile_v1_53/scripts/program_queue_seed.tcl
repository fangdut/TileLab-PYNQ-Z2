# Controlled initial state injection into the actual release ELF.
if {[llength $argv]!=2} {error "Need initial head sequence and output proof JSON"}
lassign $argv seed output
if {![string is wideinteger -strict $seed] || $seed<0 || $seed>0xffffffff} {error "Seed outside uint32"}
set argv {}
# Volatile JTAG programming only. Select JTAG boot mode with board power OFF first.
set root [file normalize [file join [file dirname [info script]] ..]]
set ws $root/pynq_z2_tile_v1_53.sdk
# Default matches a PC direct cable with its automatic 169.254/16 address.
# Pass "dhcp" for a router, or an explicit 169.254.x.y board address.
set address "169.254.200.10"
if {[llength $argv]>0} {set address [lindex $argv 0]}
set ipvalue 0
if {$address ne "dhcp"} {
 if {![regexp {^169\.254\.([0-9]{1,3})\.([0-9]{1,3})$} $address -> a b]} {error "Use dhcp or a 169.254.x.y direct-link address"}
 scan $a %d a;scan $b %d b
 if {$a<1 || $a>254 || $b>255} {error "Direct address outside usable link-local range"}
 set ipvalue [expr {(169<<24)|(254<<16)|($a<<8)|$b}]
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
source $ws/hdmi_ethernet/_ide/psinit/ps7_init.tcl
ps7_init
ps7_post_config
dow $ws/hdmi_ethernet/build/hdmi_ethernet.elf
set py [file join $::env(USERPROFILE) .cache codex-runtimes codex-primary-runtime dependencies python python.exe]
if {![file exists $py]} {set py python}
set boot [string trim [exec $py $ws/reserve_boot_id.py]]
mwr 0x100000f0 [list $boot [expr {(~$boot)&0xffffffff}]]
mwr 0x10000400 [list 0x544e4554 $ipvalue 0 0 [expr {(~$ipvalue)&0xffffffff}]]

source $root/reports/v132/queue_debug_layout.tcl
set breakpoint [bpadd -addr $q_breakpoint_address -type hw]
con -block -timeout 5
bpremove $breakpoint
proc rd {addr} {return [expr [lindex [mrd -value $addr 1] 0]]}
proc words {addr count} {set out {};foreach x [mrd -value $addr $count] {lappend out [expr {$x+0}]};return $out}
if {[rd 0x10000000]!=0x54494c33 || [rd 0x10000004]!=0x11200 || [rd 0x10000008]!=$boot} {error "Breakpoint did not reach initialized V1.18 queue"}
if {[rd 0x10000010]!=0 || [rd 0x10000014]!=0 || [rd 0x10000018]!=0 || [rd 0x10000024]!=0 || [rd 0x10000050]!=0} {error "Queue is not empty or DMA already started"}
if {[rd [expr {$q_queue_address+$q_meta}]]!=0x10000000 || [rd [expr {$q_queue_address+$q_desc}]]!=0x10001000} {error "Actual queue pointers mismatch layout"}
foreach value [words [expr {$q_queue_address+$q_slot_used}] 2] {if {$value!=0} {error "Queue still owns slots"}}
foreach value [words [expr {$q_queue_address+$q_refs}] 12] {if {$value!=0} {error "Queue references not empty"}}
set before [words 0x10000000 66]
set physical [expr {$seed%12}]
foreach offset [list $q_head $q_tail $q_last_ack] {mwr [expr {$q_queue_address+$offset}] $seed}
foreach offset [list $q_read_pos $q_write_pos] {mwr [expr {$q_queue_address+$offset}] $physical}
mwr 0x10000010 [list $seed $seed]
mwr 0x1000002c $seed
mwr 0x10000100 [list $physical $physical]
set after [words 0x10000000 66]
set raw_queue [words $q_queue_address [expr {$q_sizeof/4}]]
set f [open $output w]
puts $f "{\"seed\":$seed,\"physical_start\":$physical,\"boot_id\":$boot,\"before\":\[[join $before ,]\],\"after\":\[[join $after ,]\],\"queue_words\":\[[join $raw_queue ,]\]}"
close $f

con
after 300
targets -set -filter {name == "APU"}
if {[expr [lindex [mrd -value 0x10000000 1] 0]]!=0x54494c33 || [expr [lindex [mrd -value 0x10000008 1] 0]]!=$boot} {error "ARM application did not publish the reserved boot identity"}
# loadhw can re-extract the BIT and change its mtime without changing contents.
# Record content digests only after actual FPGA/ELF programming succeeds.
exec $py $ws/record_programming.py ethernet
puts "Programmed volatile PL configuration and ARM application. Open UART at 115200 8N1."
puts "Ethernet mode/address: $address (TCP 9133)"
disconnect
exit

