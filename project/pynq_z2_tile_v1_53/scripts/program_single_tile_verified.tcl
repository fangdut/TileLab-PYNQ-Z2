# Called only after Python verifies matching SHA256, timing, source and XSA/BIT.
if {[catch {
 if {[llength $argv]!=3} {error "Use verified program_single_tile.py entry point"}
 lassign $argv bundle boot ipvalue
 if {![string is entier -strict $boot] || $boot<=0 || $boot>=0xffffffff} {error "Invalid boot identity"}
 connect
 after 1500
 set cpus [targets -target-properties -filter {name =~ "ARM*#0"}]
 if {[llength $cpus]!=1} {error "Expected exactly one powered PYNQ-Z2 Cortex-A9 #0; select JTAG boot with power off first"}
 targets -set -filter {name =~ "ARM*#0"}
 rst -system
 after 1000
 stop
 fpga -file [file join $bundle system.bit]
 source [file join $bundle ps7_init.tcl]
 ps7_init
 ps7_post_config
 dow [file join $bundle hdmi_ethernet.elf]
 mwr 0x100000f0 [list $boot [expr {(~$boot)&0xffffffff}]]
 mwr 0x10000400 [list 0x544e4554 $ipvalue 0 0 [expr {(~$ipvalue)&0xffffffff}]]
 con
 after 1000
 targets -set -filter {name == "APU"}
 loadhw -hw [file join $bundle system.xsa]
 foreach {address expected} [list 0x10000000 0x54494c33 0x10000004 0x13200 0x10000008 $boot 0x43c00100 0xd06b3b9b 0x41210000 0x006e0186 0x41210008 0x02610379] {
  if {[expr [lindex [mrd -value $address 1] 0]]!=$expected} {error "Current firmware/model/ROI startup check failed at $address"}
 }
 disconnect
 puts "V164 volatile programming and startup register checks passed. This is not accuracy/board acceptance."
} why opts]} {
 puts stderr "PROGRAMMING_FAILED: $why"
 if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]}
 exit 1
}
exit 0
