set root [file normalize [file join [file dirname [info script]] ..]]
open_project $root/pynq_z2_tile_v1_5.xpr
open_run impl_1
set rxclks [get_clocks -include_generated_clocks hdmi_rx_clk]
set refclks [get_clocks -include_generated_clocks clk_fpga_1]
if {[llength $rxclks]<2 || [llength $refclks]<1} {error "Expected recovered and PS reference clocks are missing"}
puts "AUDIT_RX_CLOCKS=$rxclks"
puts "AUDIT_PS_CLOCKS=$refclks"
report_clock_interaction -file $root/reports/clock_interaction.rpt
report_exceptions -coverage -file $root/reports/exception_coverage.rpt
report_bus_skew -file $root/reports/bus_skew.rpt
report_methodology -file $root/reports/methodology.rpt
report_timing_summary -report_unconstrained -check_timing_verbose -file $root/reports/timing_verbose.rpt
report_utilization -hierarchical -file $root/reports/hierarchy_utilization.rpt
close_project
source $root/scripts/package_vision.tcl
