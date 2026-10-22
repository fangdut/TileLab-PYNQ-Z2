# V181 residual stream proposal (offline experiment)

The currently accepted detector is V179/HLS62, with actual8.169553FPS HDMI,
8.021126FPS fixed frame,117/117 exact originals and117/117 HDMI correct.
V180 uses the same kernel and changes DDR topology/clock; Winograd is not
integrated. V181 is an independent prospective scheduling change.

`texture_residual_stream.cpp` / frozen HLS63 changes only residual add loops.
The previous inner16-byte pipeline restarted for every packed word. A single
pipeline now spans all words in a chunk. It reads the existing left/right RAMs,
calls the same two exact rq8 paths and saturates identically. A byte shift
assembly preserves original lane order after16iterations. The three256-word
RAMs, arithmetic coefficients, model and threshold are unchanged in source.
No DSP/LUT/timing or FPGA speed benefit is claimed before implementation.

The source-bound117-photo full-output C regression is in progress. Only if it
passes, and after the current V180 physical/board trial ends, may synthesis run.
If V180 already reaches the sustained10FPS milestone, optional synthesis of
this proposal is deferred. Otherwise HLS estimates, RTL, actual mapped resource,
timing and board evidence are still required before replacing accepted hardware.
CPU C tests are offline audits only. No CPU/GPU inference fallback is introduced.
