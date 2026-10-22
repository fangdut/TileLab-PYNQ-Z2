connect -url tcp:127.0.0.1:3121
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v173_hw04/system.xsa}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != 3782341529} {error "Wrong boot"}
mwr 0x43c20000 0
set drained 0
for {set i 0} {$i<100} {incr i} {
 if {!([expr [lindex [mrd -value 0x43c20004 1] 0]] & 1)} {set drained 1;break}
 after 100
}
puts "OWNED_FAILED_VIDEO_DISABLED_AND_DRAINED $drained"
disconnect
exit