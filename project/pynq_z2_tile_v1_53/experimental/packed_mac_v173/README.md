# Packed DSP arithmetic and complete kernel candidates — not deployed

`packed_product.sv` is an isolated three-stage arithmetic block. The directory now also contains separate complete HLS detector candidates derived from frozen HLS26. The active detector remains frozen HLS23; none of these candidates has a measured board FPS. Their identical model/threshold do not make their hardware performance equivalent.

In convolution mode, one signed 25×18 DSP multiplication computes two signed INT8 products sharing an activation `x`. For signed weights `a,b`, form `A = b*2^17 + uint8(a)` and multiply `P=A*x`. Let `L` be the signed low 17 bits of `P`. Recover `a*x = L - (a<0 ? 256*x : 0)` and `b*x = (P arithmetic-shift-right 17) + (L<0)`. The unsigned low-weight representation avoids overflowing signed 25 bits when both weights are -128. The correction uses fabric add/subtract logic.

In nearest-codebook mode, the same DSP receives the sign-extended difference on both operands and produces its square. Input difference supports all signed 18-bit values; the deployed model's INT16 difference is within this range. Mode and correction metadata follow the registered data, allowing adjacent-cycle mode changes. This primitive alone does not prove that the complete HLS array shares the multipliers or meets timing.

Evidence under `reports/v173/packed_primitive`:

- Native integer mathematical check covers all 16,777,216 INT8 `(x,a,b)` triples. A separate range check covers all 262,144 signed 18-bit differences.
- RTL simulation checks 20,002 outputs, signed extremes, random values and alternating modes against separate scalar multiplication references.
- Out-of-context synthesis on xc7z020clg400-1 uses **1 DSP, 56 LUT and 92 registers**. No placed/routed timing or system speed claim is made.
- The first synthesis used two DSPs because the correction adder was also mapped to DSP. The accepted primitive explicitly assigns correction arithmetic to fabric; the failed resource report is retained.

Original code is MIT. Test values are arithmetic fixtures, not real-image accuracy evidence.

`packed_pair.cpp` expresses the same arithmetic for Vitis HLS. Its separate C simulation and RTL co-simulation pass 4096 independent scalar-reference transactions. RTL co-simulation reports latency 3 cycles, initiation interval 1. HLS estimates 1 DSP, 304 LUT and 268 FF; these HLS estimates are separate from the hand-written RTL's actual synthesis numbers above. The first HLS build failed to link because files were added before the new solution; the corrected build adds them after `open_solution`.

The complete integration processes 32 standard/pointwise output channels with the same 128 multipliers. It has two accumulator sets, 1024-bit sum packets, partial-channel masking and two output planes. Depthwise retains 16 channels; codebook search uses two full-width 64-dimensional distances. See `reports/v173/full_candidates` for source-bound evidence.

| Candidate | Exact full C regression | Complete RTL | Result |
|---|---|---|---|
| `texture_packed.cpp` / HLS27 | 117/117, scores and masks exact | Aborted; not a pass | HLS 334 BRAM18 exceeds 280-device capacity |
| `texture_packed_t2p.cpp` / HLS28 | 117/117, exact | Aborted; not a pass | True-dual-port binding alone still needs 334 BRAM18 |
| `texture_packed_wide.cpp` / HLS29 | 117/117, exact | Deferred; not a pass | 128-bit RAM reduces HLS to 270 BRAM18; actual isolated synthesis 50,893 LUT, 219 DSP, 133 BRAM tiles |
| `texture_packed_centered.cpp` / HLS30 | 117/117, exact | Two complete calls pass | Actual isolated synthesis 47,618 LUT, 65,515 FF, 218 DSP, 133 BRAM tiles; whole-video implementation pending |

HLS30 packs **signed** low weights and relies on frozen symmetric weights in [-127,127]; all 16,646,400 triples in this restricted domain pass the independent mathematical check in `check_centered.cpp`. `build_candidate.py` inspects the actual binary model and verifies all 529,760 packed convolution weight bytes, graph/task agreement, source hashes and complete C/RTL evidence before building. A weight of -128 is rejected. This domain restriction does not apply to the original general primitive.

HLS30 also uses fixed eight-group requantization and bounded address arithmetic. The RTL fixture uses a 79x65 input with internal side 80, crosses 32-pixel blocks and performs two launches to check retained state. Its reported 656,435 cycles are **not** a full 224-side detector speed. Isolated OOC synthesis is neither whole-chip fit nor routed timing. Complete HDMI implementation, original-file board regression, actual HDMI regression and measured sustained throughput remain required before promotion.

`build_detector_hls.tcl` performs C simulation, synthesis, a BRAM/DSP gate, complete RTL co-simulation and IP export in a fresh output directory. `synthesize_rtl.tcl` performs isolated generated-RTL resource synthesis only. Build folders and original evidence are never overwritten. The accepted V172 release remains recoverable throughout these experiments.
