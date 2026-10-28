# V201 clock and POR diagnostics

This is a rejected runtime-divider experiment, not a stable release. The matched
BIT already uses ps7/FCLK_CLK0 for infer/ap_clk, AXI and reset synchronization.
The50MHz divider passed201 repeated fixed-frame computations and100 logical
stop-inspect-review-dispose cycles, but failed after97of117 raw photo checks.
DDR was held in reset and the ARM was in BootROM again. After clearing history,
REBOOT_STATUS bit22 was set. This identifies a POR event; it does not identify
the electrical fault, cable, USB socket or power source without measurement.

The unaccepted_runtime_override directory preserves candidate software. It was
removed from the production source paths. No new BIT, algorithm or stable
archive has been promoted. ExistingV200 archive remains immutable. Never run
clock writes or JTAG probes concurrently with a live inspection.

AMD sources:
- https://docs.amd.com/r/en-US/ug585-zynq-7000-SoC-TRM/Register-REBOOT_STATUS-Details
- https://docs.amd.com/r/en-US/52030/Solution?contentId=KAWa6AiaUBmsxIRIR8m4JA
- https://docs.amd.com/r/en-US/ug585-zynq-7000-SoC-TRM/Glitch-Free-Divider
