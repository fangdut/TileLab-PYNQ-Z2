if {![info exists ::env(TILE_METRIC_BIST_OUT)]} {error "Set TILE_METRIC_BIST_OUT"}
set out [file normalize $::env(TILE_METRIC_BIST_OUT)]
set_param general.maxThreads 2
open_project $out/metric_bist.xpr
open_run impl_1
report_bus_skew -file $out/bus_skew.rpt
report_cdc -details -file $out/cdc.rpt
report_route_status -file $out/route_status.rpt
report_methodology -file $out/methodology.rpt
close_project
