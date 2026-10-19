# Volatile JTAG only. Invoked after Python verifies the candidate manifest.
if {[llength $argv]!=5} {error "Expected artifact directory, boot ID, IPv4 word, result file and init script"}
lassign $argv artifacts boot ipvalue result init
if {![string is wideinteger -strict $boot] || $boot<1 || $boot>0xffffffff} {error "Invalid boot identity"}
connect
after 3000
jtag targets -open -filter {name =~ "Xilinx TUL*"}
jtag targets -set -filter {name =~ "Xilinx TUL*"}
jtag frequency 1000000
set cpus [targets -target-properties -filter {name =~ "ARM*#0"}]
if {[llength $cpus]!=1} {error "Expected exactly one PYNQ-Z2 Cortex-A9 #0"}
targets -set -filter {name =~ "ARM*#0"}
rst -system
after 1000
stop
fpga -file $artifacts/system.bit
source $init
ps7_init
ps7_post_config
dow $artifacts/hdmi_ethernet/build/hdmi_ethernet.elf
mwr 0x100000f0 [list $boot [expr {(~$boot)&0xffffffff}]]
mwr 0x10000400 [list 0x544e4554 $ipvalue 0 0 [expr {(~$ipvalue)&0xffffffff}]]
con
after 300
targets -set -filter {name == "APU"}
set magic [expr [lindex [mrd -value 0x10000000 1] 0]]
set version [expr [lindex [mrd -value 0x10000004 1] 0]]
set observed_boot [expr [lindex [mrd -value 0x10000008 1] 0]]
if {$magic!=0x54494c33 || $version!=0x12d00 || $observed_boot!=$boot} {error "Candidate firmware identity was not published"}
set f [open $result {WRONLY CREAT EXCL}]
puts $f "boot_id=$boot"
puts $f "firmware_version=$version"
close $f
disconnect
exit

