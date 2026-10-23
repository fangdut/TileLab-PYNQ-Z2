if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
puts "profile_jtag_clock [jtag frequency 1000000]"
targets -set -filter {name == "APU"}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != 1344284584} {error "Boot identity changed"}
if {[expr [lindex [mrd -value 0x43c20000 1] 0]] != 0 || ([expr [lindex [mrd -value 0x43c20004 1] 0]] & 1)} {error "Video not drained"}
puts "CORE_STATE_BEGIN"
puts [targets]
puts "CORE_STATE_END"
mrd -bin -file {D:/Vivado/TileLab_RealPhotos_20261020/v186_control_profile12/trace.bin} 0x05f01000 200
puts "PROFILE_TRACE_DUMP_PASS"
disconnect
} why opts]} {puts stderr $why;exit 1}
exit 0
