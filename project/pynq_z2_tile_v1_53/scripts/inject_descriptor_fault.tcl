# Controlled lab fault: one completed, future DMA trailer while ARM is stopped.
# Caller reprograms the same accepted release afterwards to reset test counters.
set root [file normalize [file join [file dirname [info script]] ..]]
if {[llength $argv]!=1} {error "Expected the current reserved boot ID"}
set expected_boot [lindex $argv 0]
proc rd {addr} {return [expr [lindex [mrd -value $addr 1] 0]]}
proc words {addr count} {set out {};foreach w [mrd -value $addr $count] {lappend out [expr $w]};return $out}
proc descriptor_crc {data} {
 set crc 0xffffffff
 for {set i 0} {$i<40} {incr i} {
  set word [expr {$i==8?0:[lindex $data $i]}]
  set crc [expr {($crc^$word)&0xffffffff}]
  for {set b 0} {$b<32} {incr b} {set crc [expr {(($crc>>1)^(($crc&1)?0xedb88320:0))&0xffffffff}]}
 }
 return [expr {(~$crc)&0xffffffff}]
}
connect
after 500
jtag targets -open -filter {name =~ "Xilinx TUL*"}
jtag targets -set -filter {name =~ "Xilinx TUL*"}
jtag frequency 1000000
targets -set -filter {name == "APU"}
# Populate the debugger's PL address map from this exact implemented XSA,
# as in the existing read-only JTAG capture tooling.
loadhw -hw $root/pynq_z2_tile_v1_53.sdk/system.xsa
if {[rd 0x10000000]!=0x54494c33 || [rd 0x10000004]!=0x12500 || [rd 0x10000008]!=$expected_boot} {error "Expected this release's currently programmed board"}
set halted 0
set control_saved -1
try {
 targets -set -filter {name =~ "ARM*#0"}
 stop
 set halted 1
 targets -set -filter {name == "APU"}
 set before [words 0x10000000 64]
 set control_saved [rd 0x41290008]
 if {!($control_saved&2)} {error "Continuous capture is not enabled"}
 # Let a few future frames complete, then close acquisition at frame boundary.
 after 100
 mwr 0x41290008 [expr {$control_saved&~2}]
 after 100
 set chosen -1
 set chosen_seq -1
 set original {}
 set last_seq [lindex $before 19]
 for {set i 0} {$i<32} {incr i} {
  set bd [words [expr {0x10010000+$i*64}] 8]
  set address [lindex $bd 2]
  set status [lindex $bd 7]
  if {!($status&0x80000000) || ($status&0x70000000) || ($status&0x03ffffff)!=3686560} {continue}
  if {$address<0x10100000 || $address>=0x1c100000 || (($address-0x10100000)%0x400000)!=0} {error "DMA slot address outside this design's 48 buffers"}
  set trailer [expr {$address+3686400}]
  set data [words $trailer 40]
  set seq [lindex $data 2]
  # Later than the currently consumed frame; never patch a CPU-local copy.
  if {[lindex $data 0]!=0x54465337 || $seq<=$last_seq+2 || $seq<=$chosen_seq} {continue}
  if {([lindex $data 6]|[lindex $data 9])&0x80000000} {continue}
  if {[descriptor_crc $data]!=[lindex $data 8]} {error "Selected pristine descriptor already has invalid CRC"}
  set chosen $trailer;set chosen_seq $seq;set original $data;set chosen_bd $i
 }
 if {$chosen<0} {error "No future completed valid DMA descriptor available for bounded fault test"}
 set changed [expr {$chosen_seq^1}]
 mwr [expr {$chosen+8}] $changed
 if {[rd [expr {$chosen+8}]]!=$changed} {error "Single-bit test write was not observed"}
 targets -set -filter {name =~ "ARM*#0"}
 con
 set halted 0
 after 500
 targets -set -filter {name == "APU"}
 set result [words 0x10000000 64]
 if {[lindex $result 37]!=[lindex $before 37]+1} {error "Expected exactly one descriptor CRC rejection"}
 if {[lindex $result 10]<[lindex $before 10]+1 || [lindex $result 38]<=[lindex $before 38]} {error "Rejection/continued valid consumption counters failed"}
 set f [open $root/reports/v137/descriptor_fault_raw.json w]
 puts $f "{\"passed\":true,\"boot_id\":$expected_boot,\"descriptor_address\":$chosen,\"bd_index\":$chosen_bd,\"original_seq\":$chosen_seq,\"changed_seq\":$changed,\"original_words\":\[[join $original ,]\],\"before\":\[[join $before ,]\],\"after\":\[[join $result ,]\]}"
 close $f
 puts "PASS actual DMA trailer bit flip rejected by ARM CRC before queue decisions"
} finally {
 if {$halted} {catch {targets -set -filter {name =~ "ARM*#0"};con}}
 if {$control_saved>=0} {catch {targets -set -filter {name == "APU"};mwr 0x41290008 $control_saved}}
 disconnect
}
exit
