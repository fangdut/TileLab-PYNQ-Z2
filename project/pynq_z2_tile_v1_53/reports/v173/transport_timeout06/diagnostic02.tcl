connect -url tcp:127.0.0.1:3121
targets -set -filter {name =~ "ARM*#0"}
if {[catch {stop} why] && $why ne "Already stopped"} {error $why}
puts "ARM0_PC [rrd pc]"
puts "ARM0_CPSR [rrd cpsr]"
targets -set -filter {name =~ "ARM*#1"}
if {[catch {stop} why] && $why ne "Already stopped"} {error $why}
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v173_hw04/system.xsa}
puts "CLIENT_STATE [mrd -value 0x00200020 8]"
puts "TX_STATE [mrd -value 0x00200438 4]"
puts "TX_ACK [mrd -value 0x002004dc 1]"
puts "TCP_PCB_HEADS [mrd -value 0x0030ee48 6]"
puts "ETHERNET_REGISTERS [mrd -value 0xe000b000 16]"
disconnect
exit
