# Packed DSP arithmetic prototype — not deployed

`packed_product.sv` is an isolated three-stage arithmetic block. It is not yet connected to the CNN, does not change the deployed model, and has no measured detector FPS. The active detector remains frozen HLS23. Full-array memory banking, weight loading, accumulation, scheduling, implementation timing and all-photo regression remain necessary before integration can be accepted.

In convolution mode, one signed 25×18 DSP multiplication computes two signed INT8 products sharing an activation `x`. For signed weights `a,b`, form `A = b*2^17 + uint8(a)` and multiply `P=A*x`. Let `L` be the signed low 17 bits of `P`. Recover `a*x = L - (a<0 ? 256*x : 0)` and `b*x = (P arithmetic-shift-right 17) + (L<0)`. The unsigned low-weight representation avoids overflowing signed 25 bits when both weights are -128. The correction uses fabric add/subtract logic.

In nearest-codebook mode, the same DSP receives the sign-extended difference on both operands and produces its square. Input difference supports all signed 18-bit values; the deployed model's INT16 difference is within this range. Mode and correction metadata follow the registered data, allowing adjacent-cycle mode changes. This primitive alone does not prove that the complete HLS array shares the multipliers or meets timing.

Evidence under `reports/v173/packed_primitive`:

- Native integer mathematical check covers all 16,777,216 INT8 `(x,a,b)` triples. A separate range check covers all 262,144 signed 18-bit differences.
- RTL simulation checks 20,002 outputs, signed extremes, random values and alternating modes against separate scalar multiplication references.
- Out-of-context synthesis on xc7z020clg400-1 uses **1 DSP, 56 LUT and 92 registers**. No placed/routed timing or system speed claim is made.
- The first synthesis used two DSPs because the correction adder was also mapped to DSP. The accepted primitive explicitly assigns correction arithmetic to fabric; the failed resource report is retained.

Original code is MIT. Test values are arithmetic fixtures, not real-image accuracy evidence.

`packed_pair.cpp` expresses the same arithmetic for Vitis HLS. Its separate C simulation and RTL co-simulation pass 4096 independent scalar-reference transactions. RTL co-simulation reports latency 3 cycles, initiation interval 1. HLS estimates 1 DSP, 304 LUT and 268 FF; these HLS estimates are separate from the hand-written RTL's actual synthesis numbers above. The first HLS build failed to link because files were added before the new solution; the corrected build adds them after `open_solution`.

The next integration can retain the 16 existing 64-bit RAM banks and use both ports to read two output-channel groups. Each packed PE then produces one result for each of those two groups. Pointwise convolution processes 32 output channels per block using the same 128 multiplier count. Depthwise convolution retains its current 16-channel path. Codebook search still uses the full-width square mode with two 64-dimensional centers per cycle. Required changes include two sets of accumulators, output packets, requantization, final partial-channel masking and two-plane DDR writes. This is a design direction, not an implemented or tested complete detector.
