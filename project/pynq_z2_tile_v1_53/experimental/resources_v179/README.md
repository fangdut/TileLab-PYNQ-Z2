# V179 exact resource redistribution (experimental)

Runtime image processing remains FPGA PL. Native C tests are offline numerical
audits, not a CPU inference fallback or FPGA performance measurement. The frozen
model, quantization, threshold and masks are unchanged.

The accepted board remains V173 R2/HLS39: 6.665890 FPS continuous HDMI, 7.538925
FPS fixed frame. V176 and V178 125 MHz builds fail timing and were never
programmed. Repeating placement on a large timing deficit is deliberately
bounded; see `reports/v176/hw03_125mhz_rejected` and
`reports/v178/hw01_125mhz_rejected`.

Changes in the latest source `texture_bounded_inline.cpp` / frozen HLS61:

* Keep exact spatial-coordinate and feature-layout ROMs from V176/V178.
* Depthwise logical span 32 -> 16 avoids invalid work on small feature maps.
  Static analysis checks the actual shorter accumulator reuse distance, not
  merely allocated RAM depth. This does not halve whole-network latency.
* Projection 8 -> 16 lanes reuses existing 16-bank storage. Redirect one of
  four requantization lanes and the normalization multiply to pipelined fabric
  arithmetic to fund additional projection DSPs.
* Split the wide normalization multiply into seven exact nibble products and
  staged sums. A simple fabric binding failed the clock estimate (HLS57).
* Bound bilinear interpolation to 8x9 horizontal products, 17-bit horizontal
  sums, and 17x9 vertical products. Since den<=448, the full nonnegative sum
  is <=255*448^2=51,179,520 <2^26. The original wider products wasted DSPs.
  HLS60 passes C117 but crashes the legacy HLS frontend. HLS61 keeps the same
  arithmetic, inlines this helper, and removes its explicit DSP bindings;
  synthesis then completes. The exact compiler crash cause is not established.

HLS61 synthesis estimates 214 DSP, 251 BRAM18, 71,767 LUT, 70,073 FF,
8.207ns (121.85MHz). These are HLS estimates; actual mapped DSP/LUT counts,
whole-system timing and board speed must still be checked. Prior HLS56
estimated 217 DSP but actually mapped 219: do not infer hardware use from HLS.

Independent C scalar checks bind frozen HLS61 and compare exact wide native
integer reference results: 131,248 bilinear cases (all 217 legal sizes plus
random cases), 100,072 normalization cases, 100,088 requantization cases.
See `reports/v179/scalar61`. Full 117-photo regressions bind each source hash;
complete output file comparisons to accepted HLS39 are archived separately.
These repeatedly exposed development photos are not a blind accuracy test.

`build_bounded_inline_full_hls.tcl` uses source-identical HLS62 for complete
reduced-fixture RTL co-simulation and IP export after all source-bound C and
scalar gates pass. Physical implementation and board acceptance follow
separately. No sustained 10 FPS, achieved 125 MHz, new accepted release or
award readiness is claimed by these experiments.

Original code MIT; dataset-derived model/evidence retains its existing license.
