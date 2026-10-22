# V176 bounded geometry and clock scheduling experiment

This is an unaccepted experiment. Stable board hardware remains V173R2/HLS39.

V175 HW02 fails 100MHz setup at -0.482ns; one physical repair reaches -0.279ns
and is still rejected. The original worst path runs from sub_ln527 to icmp_ln528
in the HLS39 feature-layout multiplication and capacity guard.

texture_geometry_lut.cpp replaces this layout with a packed 32-word ROM. The
existing header guard bounds side to8..224 and grid to side/8. All217 possible
sides have feature lengths that fit11bits each; their sum is at most2744,
within the existing4096-word feature cache. The removed overflow branch cannot
be taken after that existing guard. Neural arithmetic, frozen weights and
threshold10908 are unchanged. test_geometry.py checks all32 words and217 sides.

The source is frozen as v170_hls52.cpp and source-identical v170_hls53.cpp. The reduced79x65/internal80/nine-task
two-launch C fixture passes, and all117 original-photo output files are byte-identical to HLS39.
The separate build_125mhz_hls.tcl uses an8ns period with0.8ns uncertainty to
evaluate additional pipeline stages. The current launch is synthesis only;
it does not run RTL, export a deployable IP, program hardware or prove125MHz.
HLS52 estimates8.207ns/121.85MHz, which misses125MHz. All loop constraints pass;
16 accumulator banks read at stage23 and write32, before the next32-slot read.
Estimated resources:219DSP/251BRAM18/66568LUT/67028FF. These are not actual
Vivado resource measurements. Source-identical HLS53 is running the full RTL/IP flow.

build_candidate.py --clock-mhz125 requires an HLS target period at most8ns,
and the hardware export checks the actual Vivado PL clock period. The old10ns
HLS39 request at125MHz is rejected before launching Vivado. HPD startup is
scaled with the chosen100/125MHz clock to retain200ms. Existing100MHz defaults
and accepted compiled artifacts remain unchanged.

Next gates: full117 exact output files, synthesized capacities/recurrences,
resource synthesis, two retained-fixture RTL launches, complete HDMI physical
timing and both Gray skew constraints, then real HDMI/ARM-halt board testing.
Higher clock targets are retained only if measured end-to-end throughput and
accuracy pass. The V175 overlap RTL is separately tested but not accepted.
