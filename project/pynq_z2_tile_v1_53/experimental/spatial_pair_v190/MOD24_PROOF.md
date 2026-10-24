# HLS79: exact accumulator width and quantization mapping

This is an experimental hardware transformation, not a claim of FPGA fit or FPS. Model bytes, resolution, bias, multiplier, thresholds and nearest-neighbor distances remain unchanged.

Let R24(x) be the signed representative of x modulo2^24. The original quant_row adds a signed32 bias to each signed32 convolution sum, then explicitly converts that result to ap_int24 before multiplying. Its observable operand is R24(sum+bias).

Modular reduction commutes with addition: R24(R24(a)+b)=R24(a+b). Induction over taps proves that reducing each intermediate accumulator produces the same final operand after bias addition. Signed32 wrap cannot affect this identity because2^24 divides2^32. Sign-extending signed24 to the existing signed32 packet field preserves the operand. This need not preserve the full32 raw MAC value; tests compare its signed24 representative and independently check quantized output.

The convolution packet consumer is quant_row. It uses no discarded bits for decisions, saturation, rounding or statistics. The signed24 conversion occurs before requantization and clipping in both sources. Adversarial testing crosses0x7fffff and includes both signed32 bias extremes, signed24 bias boundaries and two multipliers.

Depthwise has at most nine signed8 products, magnitude at most9*16384=147456, within signed24. Nearest-neighbor does not access these accumulators; its arithmetic, two64bit distances and invalid-center sentinel remain unchanged.

The previous fourth quantizer uses fabric partial products. Its replacement calls rq_dsp for the same signed24 by unsigned27 product in52 bits and the same rounding. Product magnitude is less than2^50; this representation is exact. There is no new approximation or scale selection.

The estimate gate reserves four DSPs beyond the HLS estimate. The complete mapped HDMI design must still use at most220 DSPs and140 BRAM36 tiles and pass placement, routing and timing. No physical device capacity gate is relaxed.

Independent scalar tests, generated MAC RTL with backpressure and explicit overflow, complete AXI RTL, all117 exposed development photos, full implementation and physical direct/HDMI acceptance remain separate gates. Offline simulation duration is never board FPS. HLS78 failed compilation because mixed24/32bit conditionals required explicit casts; its source and failure logs are retained.
