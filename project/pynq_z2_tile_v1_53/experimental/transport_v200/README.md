# V200 closed-loop reference control

The100MHz PL bitstream and CNN/projection are unchanged. The two deployed
profiles differ only in the preexisting normal centers and threshold. The
firmware explicitly allows their CRCs and exposes a32-byte capability reply
to status requests. A new upload invalidates the cached frame dimensions.
The host verifies complete profile SHA256 values and compiled registry binding.

`prepare_profiles.py` requires the hash-verified V199 bundle, the prior V195R2
roof reference, and the matching BSP's vendor xadapter.c. It emits a sealed
profile directory and control firmware. Firmware outputs are also retained in
`firmware/` for inspection and rebuilding. `TILE_TEXTURE_TRANSPORT_SOURCE`
selects this main.c for scripts/texture_v170/rebuild_transport.py. Provide a
fresh output workspace and the matched existing BSP, hardware and primary
texture model. Do not overwrite a verified workspace or copy stale headers.

The generated xadapter_guarded.c and xemacpsif_physpeed_guarded.c retain their
AMD/Xilinx notices. On the Realtek link recovery path, the adapter reads an
already negotiated speed rather than resetting/renegotiating inside the TCP
loop. Invalid speeds remain negotiating instead of entering a MAC assertion.
The vendor clock-setting body is unchanged and exported for this transition.
The original unsuccessful startup and a separate39-frame/DDR-reset batch are
retained in reports/v200. The root cause of that DDR reset is not established.

The workstation implements material binding, at least3 distinct normal checks
plus1 known defect, immutable qualification certificates, mandatory recorded
review and disposition. This is verification of a deployed frozen reference,
not online learning or an independent accuracy certificate. No image inference
is added to ARM or PC. The API and browser review tests use openly marked
automated actors and exposed labels, not real human review.

See host/stop_inspect_station/CLOSED_LOOP.md and reports/v200/status.html.
The117-photo replay uses a1-second inter-case pause; it does not establish
continuous high-duty stability. Programming is volatile only, never Flash.
