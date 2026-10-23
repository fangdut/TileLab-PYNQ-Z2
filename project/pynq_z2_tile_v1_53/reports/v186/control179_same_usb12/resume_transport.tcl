if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
puts "resume_jtag_clock [jtag frequency 1000000]"
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.xsa}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != 1344284584} {error "Unexpected control boot"}
if {[expr [lindex [mrd -value 0x43c20000 1] 0]] != 0 || ([expr [lindex [mrd -value 0x43c20004 1] 0]] & 1)} {error "Video still owns frame"}
if {!([expr [lindex [mrd -value 0x43c10000 1] 0]] & 4)} {error "Detector not idle"}
targets -set -filter {name =~ "ARM*#0"}
con
puts "ARM0_TRANSPORT_RESUMED_AFTER_VIDEO_STOPPED"
puts [targets]
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
