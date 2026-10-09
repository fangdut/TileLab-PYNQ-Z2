# Persistent debug transport. No image recognition is performed by this bridge.
# Native packet capture and candidate metadata come from the same FPGA frame.
set root [file normalize [file join [file dirname [info script]] ..]]
set run $root/host/runtime
file mkdir $run
proc atomic_write {path text} {set f [open ${path}.tmp w];puts $f $text;close $f;file rename -force ${path}.tmp $path}
proc rd {addr} {return [expr [lindex [mrd -value $addr 1] 0]]}
connect
after 1000
targets -set -filter {name == "APU"}
loadhw -hw $root/pynq_z2_tile_v1_53.sdk/system.xsa
set last ""
atomic_write $run/bridge_state.txt "ready"
while {![file exists $run/stop]} {
 if {![file exists $run/request.txt]} {after 100;continue}
 set f [open $run/request.txt r];set line [string trim [read $f]];close $f
 if {$line eq $last} {after 100;continue}
 set last $line
 if {![regexp {^capture ([0-9]+) ([0-9]+)$} $line -> id threshold]} {after 100;continue}
 if {$threshold<1 || $threshold>255} {continue}
 set started [clock milliseconds]
 if {[catch {
  # Publish parameters as one existing config_bridge transaction at VS.
  set oldcfg [rd 0x41200008]
  set word [expr {(($oldcfg ^ 0x80000000)&0x80000000)|0x00f30007|($threshold<<8)}]
  mwr 0x41210000 0x00500050
  mwr 0x41210008 0x027f04af
  mwr 0x41200008 $word
  after 60
  set before [rd 0x41290000]
  set token [expr {([rd 0x41290008]^1)&1}]
  # DMA uses the reserved DDR region 0x10000000..0x10383fff.
  mwr 0x40400030 4
  set deadline [expr {[clock milliseconds]+1000}]
  while {([rd 0x40400030]&4)!=0} {if {[clock milliseconds]>$deadline} {error "DMA reset timeout"};after 2}
  mwr 0x40400034 0x7000
  mwr 0x40400030 1
  mwr 0x40400048 0x10000000
  mwr 0x40400058 3686400
  mwr 0x41290008 $token
  set deadline [expr {[clock milliseconds]+2500}]
  while {1} {
   set seq [rd 0x41290000];set status [rd 0x412b0008];set dma [rd 0x40400034]
   if {$seq!=$before && ($status&1)==$token && ($status&4)} {
    if {$status&0x80000000} {error "Capture invalid: video overrun or wrong geometry"}
    if {$dma&0x70} {error [format "DMA error 0x%08x" $dma]}
    if {$dma&2} {break}
   }
   if {[clock milliseconds]>$deadline} {error [format "Capture timeout seq=%u status=%08x dma=%08x" $seq $status $dma]}
   after 5
  }
  set count [rd 0x412a0000];set lo [rd 0x412a0008];set hi [rd 0x412b0000];set cfg [rd 0x412c0000]
  mrd -bin -file $run/frame_${id}.bin 0x10000000 921600
  set frames [rd 0x41200000]
  set elapsed [expr {[clock milliseconds]-$started}]
  atomic_write $run/response.txt "ok $id $seq $count $lo $hi $status $cfg $frames $elapsed"
 } err]} {
  # No old image is relabeled as a new successful capture on any error.
  set safe [string map {\n { } \r { }} $err]
  atomic_write $run/response.txt "error $id $safe"
 }
}
atomic_write $run/bridge_state.txt "stopped"
disconnect
exit
