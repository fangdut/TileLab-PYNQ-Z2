# CPU owns capture/DMA. Retained frames remain immutable until explicit ACK.
set root [file normalize [file join [file dirname [info script]] ..]]
set run $root/host/runtime
file mkdir $run
proc atomic_write {path text} {
 set f [open ${path}.tmp w];puts $f $text;close $f
 for {set n 0} {$n<100} {incr n} {
  if {![catch {file rename -force ${path}.tmp $path} error]} {return}
  after 10
 }
 error $error
}
proc rd {addr} {return [expr [lindex [mrd -value $addr 1] 0]]}
proc words {addr count} {set out {};foreach x [mrd -value $addr $count] {lappend out [expr $x]};return $out}
connect
after 500
targets -set -filter {name == "APU"}
loadhw -hw $root/pynq_z2_tile_v1_53.sdk/system.xsa
if {[rd 0x10000000]!=0x54494c33} {error "Compatible Tile queue firmware not running"}
mwr 0x10000040 1
set last ""
atomic_write $run/bridge_state.txt ready
while {![file exists $run/stop]} {
 if {![file exists $run/request.txt]} {after 50;continue}
 if {[catch {set f [open $run/request.txt r]}]} {after 10;continue}
 set line [string trim [read $f]];close $f
 if {$line eq $last} {after 50;continue};set last $line
 set id [lindex $line 1]
 if {[catch {
  if {[regexp {^status ([0-9]+) 0$} $line -> id]} {
   atomic_write $run/response.txt "status $id [join [words 0x10000000 24] { }]"
  } elseif {[regexp {^ack ([0-9]+) ([0-9]+) ([0-9]+)$} $line -> id boot event]} {
   if {[rd 0x10000008]!=$boot} {error "Board restarted before ACK"}
   if {$event>0xffffffff} {error "Event outside 32-bit sequence"}
   set head [rd 0x10000010]
   if {$event!=$head} {
    if {$event!=[expr {($head+1)&0xffffffff}]} {error "ACK is not the queue front"}
    if {[rd 0x10000014]==$head} {error "ACK has no pending event; future confirmation rejected"}
    mwr 0x1000002c $event
    set deadline [expr {[clock milliseconds]+1500}]
    while {1} {
     if {[rd 0x10000008]!=$boot} {error "Board restarted during ACK"}
     set current [rd 0x10000010]
     if {$current==$event} {break}
     if {$current!=$head} {error "Queue identity changed during ACK"}
     if {[clock milliseconds]>$deadline} {error "Queue ACK timeout"}
     after 5
    }
   }
   atomic_write $run/response.txt "ack $id"
  } elseif {[regexp {^capture ([0-9]+) ([0-9]+)$} $line -> id threshold]} {
   if {$threshold<1 || $threshold>255} {error "Threshold outside 1..255"}
   set started [clock milliseconds]
   mwr 0x1000003c $threshold
   if {[rd 0x10000010]==[rd 0x10000014]} {
    set request [expr {([rd 0x10000038]+1)&0xffffffff}]
    mwr 0x10000034 2
    mwr 0x10000030 $request
   }
   set deadline [expr {[clock milliseconds]+3000}]
   while {[rd 0x10000010]==[rd 0x10000014]} {if {[clock milliseconds]>$deadline} {error "No completed FPGA frame; check HDMI and queue firmware"};after 10}
   set head [rd 0x10000010];set boot [rd 0x10000008]
   set version [rd 0x10000004]
   if {$version>=0x11100} {set pos [rd 0x10000100]} else {set pos [expr {$head%12}]}
   if {$pos<0 || $pos>=12} {error "Invalid physical queue position"}
   set descaddr [expr {0x10001000+$pos*160}]
   set desc [words $descaddr 40]
   if {[lindex $desc 0]!=[expr {($head+1)&0xffffffff}] || [lindex $desc 34]!=$boot || [lindex $desc 35]!=3686400} {error "Inconsistent queue descriptor"}
   set addr [lindex $desc 1]
   set end [expr {$version>=0x11100?0x1c100000:0x13100000}]
   if {$addr<0x10100000 || $addr+3686400>$end || (($addr-0x10100000)%0x400000)!=0} {error "Frame address outside retained slots"}
   mrd -bin -file $run/frame_${id}.bin $addr 921600
   if {[rd $descaddr]!=[lindex $desc 0] || [rd 0x10000008]!=$boot || [rd 0x10000010]!=$head} {error "Board restarted or frame changed during transfer"}
   set meta [words 0x10000000 24]
   set elapsed [expr {[clock milliseconds]-$started}]
   atomic_write $run/response.txt "ok $id $elapsed [join $desc { }] [join $meta { }]"
  } else {error "Unsupported request"}
 } err]} {atomic_write $run/response.txt "error $id [string map {\n { } \r { }} $err]"}
}
atomic_write $run/bridge_state.txt stopped
disconnect
exit
