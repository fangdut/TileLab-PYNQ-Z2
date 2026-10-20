# Transport experiment only: preserve the routed V164 detector, decouple HDMI
# input hotplug from HDMI output monitor presence. Never overwrite its release.
set_param general.maxThreads 2
foreach name {TILE_HEADLESS_DCP TILE_HEADLESS_OUT} {if {![info exists ::env($name)]} {error "Set $name"}}
set out [file normalize $::env(TILE_HEADLESS_OUT)]
if {[file exists $out]} {error "Output already exists"}
file mkdir $out
open_checkpoint $::env(TILE_HEADLESS_DCP)
set pin [get_pins hdmi_in_hpd_OBUF_inst/I]
if {[llength $pin]!=1} {error "Unexpected HDMI HPD structure"}
set original [get_nets -of_objects $pin]
set f [open $out/eco_change.txt w];puts $f "Only changed connection: $pin from $original to independent VCC";close $f
disconnect_net -net $original -objects $pin
create_cell -reference VCC tilelab_headless_vcc
create_net tilelab_headless_hpd
connect_net -net tilelab_headless_hpd -objects [list [get_pins tilelab_headless_vcc/P] $pin]
route_design -preserve
report_timing_summary -file $out/timing_summary.rpt
report_drc -file $out/drc.rpt
report_route_status -file $out/route_status.rpt
report_utilization -file $out/utilization.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
set errors [llength [get_drc_violations -quiet -filter {SEVERITY == Error}]]
set f [open $out/implementation_status.txt w];puts $f "setup_slack_ns=$setup";puts $f "hold_slack_ns=$hold";puts $f "drc_errors=$errors";close $f
if {$setup<0 || $hold<0 || $errors>0} {error "ECO timing/DRC failed; no bitstream exported"}
write_checkpoint $out/headless_routed.dcp
write_bitstream $out/headless_transport.bit
close_design
