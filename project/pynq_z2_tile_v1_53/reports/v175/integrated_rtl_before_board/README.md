# V175 integration regression checkpoint

Six RTL groups pass with source hashes. These use queue/control/DDR bus models;
they do not run the production CNN, prove physical timing, or measure real FPS.
The retained gate contains original local paths; archived per-role summaries and
logs preserve matching bytes. Reproduction uses fresh output folders and the
test scripts in experimental/video_overlap_v175.

HW01 failed before synthesis because the BD HPD top used a .sv extension.
The same Verilog-compatible module was renamed .v and its unit test repeated.
HW02 is building with accepted HLS39 and the complete versioned video variant.
Do not infer an accepted V175 bitstream from this checkpoint.
