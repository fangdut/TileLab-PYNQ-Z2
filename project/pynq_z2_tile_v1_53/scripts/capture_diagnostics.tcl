set root [file normalize [file join [file dirname [info script]] ..]]
connect
targets -set -filter {name == "APU"}
loadhw -hw $root/pynq_z2_tile_v1_5.sdk/system.xsa
foreach addr {0x40400030 0x40400034 0x40400048 0x40400058 0x41290000 0x41290008 0x412a0000 0x412a0008 0x412b0000 0x412b0008 0x412c0000} {
 puts [mrd $addr 1]
}
puts [mrd 0x10000000 16]
puts [mrd 0x10383fc0 16]
disconnect
exit
