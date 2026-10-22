# V177 DW scheduling candidate — not accepted hardware

The accepted board remains V173R2/HLS39. V176/HLS53 is independently undergoing
125MHz whole-system implementation; this folder does not change that trial.

Depthwise convolution uses16 spatial positions per MAC group instead of32.
Other convolutions and nearest-codebook search keep32. The allocated accumulator
RAM remains32 slots. This reduces padding work for14-column output maps.
Static counts on the frozen47-task graph change DW MAC-loop iterations from
1733760 to1338624 (-22.79%); this excludes other operations, DDR and overhead,
and is not a measured latency or whole-system FPS improvement.

The source is frozen as HLS54, derived from HLS53 with the same geometry ROM.
An8ns-target HLS synthesis passes the retained two-launch C fixture and estimates
219DSP/251BRAM18/66615LUT/67055FF. Estimated clock8.207ns still misses125MHz.
No full RTL co-simulation, actual Vivado resource use or board result exists yet.
The117-photo complete C output regression is running.

Generated RTL has accumulator read23/write32: delta9, before the next16-iteration
DW read. check_mac_recurrence.py now checks the shorter logical reuse interval,
not just allocated RAM depth. test_recurrence_guard.py injects a synthetic
20-cycle hazard, which would fit32 allocated entries but must fail16-cycle reuse.
It tests the static guard only and does not simulate the synthetic RTL.

Complete C117, full RTL, physical timing/resources/CDC and real HDMI/ARM-halt
tests remain required before any deployment or speed claim. Weights and
threshold10908 are unchanged.
