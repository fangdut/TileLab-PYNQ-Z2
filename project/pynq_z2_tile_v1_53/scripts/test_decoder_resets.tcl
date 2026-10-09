set root [file normalize [file join [file dirname [info script]] ..]]
set dir $root/reports/v132/reset_sim
create_project reset_test $dir -part xc7z020clg400-1 -force
set ip $root/ip_repo/dvi2rgb_v1_7/src
add_files [list $ip/SyncAsync.vhd $ip/SyncAsyncReset.vhd $ip/DecoderResetDomains.vhd $ip/SyncBase.vhd]
add_files -fileset sim_1 $root/sim/tb_decoder_resets.vhd
set_property FILE_TYPE {VHDL 2008} [get_files tb_decoder_resets.vhd]
set_property top tb_decoder_resets [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
set f [open $dir/reset_test.sim/sim_1/behav/xsim/simulate.log r];set result [read $f];close $f
if {![string match {*PASS V131 decoder resets:*} $result]} {error "Required reset test PASS marker missing"}
close_project
exit
