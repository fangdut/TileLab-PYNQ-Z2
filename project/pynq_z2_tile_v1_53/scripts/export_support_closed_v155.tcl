# Keep the implementation run's registered BIT/DCP aligned before XSA export.
set root [file normalize [file join [file dirname [info script]] ..]]
if {![file exists $root/CANDIDATE_BUILD_ONLY]} {error "Isolated build marker required"}
cd $root
set out $root/reports/v155/hardware_run04
set old $root/reports/v155/hardware_run03
set run $root/pynq_z2_tile_v1_53.runs/impl_1
file mkdir $old
if {![file exists $old/before_physical_optimization.bit]} {file copy $run/system_wrapper.bit $old/before_physical_optimization.bit}
if {![file exists $old/before_physical_optimization.dcp]} {file copy $run/system_wrapper_routed.dcp $old/before_physical_optimization.dcp}
file copy -force $out/system.bit $run/system_wrapper.bit
file copy -force $out/system_timing_closed.dcp $run/system_wrapper_routed.dcp
open_project $root/pynq_z2_tile_v1_53.xpr
open_run impl_1
if {[get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]<0} {error "Registered checkpoint is not timing-closed"}
if {[file exists $out/system.xsa] && ![file exists $out/system_before_matching_export.xsa]} {file copy $out/system.xsa $out/system_before_matching_export.xsa}
write_hw_platform -fixed -include_bit -force -file $out/system.xsa
close_project
