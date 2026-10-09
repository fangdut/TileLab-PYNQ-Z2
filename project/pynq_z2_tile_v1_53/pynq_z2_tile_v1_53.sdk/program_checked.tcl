# Catch XSDB command errors: native exit status alone was insufficient in older scripts.
set ws [file dirname [file normalize [info script]]]
if {[catch {source [file join $ws program_ethernet.tcl]} reason options]} {
 puts stderr "PROGRAMMING_FAILED: $reason"
 if {[dict exists $options -errorinfo]} {puts stderr [dict get $options -errorinfo]}
 exit 1
}
exit 0
