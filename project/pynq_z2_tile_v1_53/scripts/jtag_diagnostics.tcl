connect
after 1500
puts [jtag targets]
jtag targets -open -filter {name =~ "Xilinx TUL*"}
jtag targets -set -filter {name =~ "Xilinx TUL*"}
puts "JTAG_FREQUENCY=[jtag frequency 1000000]"
after 2000
puts [jtag targets]
puts [targets]
disconnect
exit
