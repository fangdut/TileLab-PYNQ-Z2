set root [file normalize [file join [file dirname [info script]] ..]]
proc source_mode {root mode} {set f [open $root/host/display_command.txt w];puts $f $mode;close $f}
connect
targets -set -filter {name == "APU"}
source_mode $root station_0
after 500
set out [open $root/reports/burst_hardware_trace.csv w]
puts $out "wall_ms,frame,status"
source_mode $root burst
set deadline [expr {[clock milliseconds]+45000}]
while {[clock milliseconds]<$deadline} {
 set values [mrd -value 0x43c00000 2]
 puts $out "[clock milliseconds],[expr [lindex $values 0]],[expr [lindex $values 1]]"
 if {![catch {set f [open $root/host/player_status.json r];set player [read $f];close $f}]} {
  if {[string match {*"source":"burst"*} $player] && [regexp {"position_seconds":([0-9.]+)} $player -> pos] && $pos>=9.5} {break}
 }
 after 5
}
close $out
source_mode $root station_0
disconnect
exit
