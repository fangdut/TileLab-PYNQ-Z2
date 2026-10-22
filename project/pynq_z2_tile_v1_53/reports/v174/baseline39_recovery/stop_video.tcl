connect -url tcp:127.0.0.1:3121
 targets -set -filter {name == "APU"}
 loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v173_hw04/system.xsa}
 if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != 501041710} {error "Wrong boot"}
 mwr 0x43c20000 0
 set drained 0
 for {set i 0} {$i<100} {incr i} {
  if {!([expr [lindex [mrd -value 0x43c20004 1] 0]] & 1)} {set drained 1;break}
  after 100
 }
 if {!$drained} {error "Owned video failed to drain"}
 puts "OWNED_BASELINE_VIDEO_DISABLED_AND_DRAINED"
 disconnect
 exit
 