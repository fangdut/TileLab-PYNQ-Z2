# V180 integer Winograd feasibility — not an implemented detector

V179 remains the active hardware candidate. This directory only evaluates an
algorithm alternative while that candidate implements. It is not linked into
the current kernel, has no HLS/RTL/board result, and is not a CPU vision fallback.

Background: [Lavin and Gray, CVPR 2016, Fast Algorithms for Convolutional Neural
Networks](https://arxiv.org/abs/1509.09308). Winograd is existing prior work.
Any project contribution would be its exact bounded implementation and resource
sharing in this detector, supported by actual board evidence, not invention of
Winograd itself.

`test_exact_transform.cpp` evaluates F(2x2,3x3) cross-correlation with integer
BT and AT and G2=2G. The transformed product therefore produces four times the
direct integer convolution, allowing an exact final division by4 before bias
and the existing requantization. No model, threshold or precision is changed
in this feasibility test.

All144 input/kernel basis pairs verify all576 bilinear output coefficients
before division. Both sides are bilinear maps; these coefficient identities
establish exact equality on all legal signed8 inputs/weights.64 extreme pattern
pairs and100000 random pairs also pass, totaling100208 cases. These use wide
native integers and do not establish a finite-width RTL implementation.

Conservative finite-width requirements derived separately:

* Input transform lies in[-512,511], so signed10 is sufficient. Each BT row
  has two signed unit entries and sum0 or2; its tensor coefficients give a
  maximum508 or510 and minimum-512.
* Scaled weight transform absolute value <=9*128=1152, fitting signed12.
* Elementwise product absolute value <=512*1152=589824; signed22 is safe.
* AT has row L1 norm3, so a scaled output sum has absolute value
  <=9*589824=5308416 <2^23, fitting signed24. Partial sums also fit that bound.
* Exact coefficient identity guarantees divisibility by4. No fractional
  rounding or new quantization error should be introduced before original bias.

The frozen224 model has10 eligible stride1 depthwise layers with even output
dimensions. Their mathematical scalar product count decreases from15128064
to6723584 (55.56%). This concerns only these layers, excluding transforms,
padding, data movement, other CNN layers and the head; it is not an FPS claim.
Stride2 and unsupported geometries require the existing direct fallback.

A conservative four-row capacity check including all channel groups peaks
at2016 packed128-bit words, below existing LD=2048. This bound alone does not
prove actual port bandwidth or a feasible storage schedule. A hardware design
must overlap tile transforms with products, account for two output rows, and
prove BRAM port ownership. Projection scratch storage is dead during eligible
depthwise layers and is a potential reuse target; reuse is not implemented.

Before changing the deployed kernel: ensure direct and transformed products
share one16-lane DSP array (a second independently outlined array would exceed
capacity), maintain the existing128-DSP convolution/distance array, validate
padding and row order, then repeat full117 C/reference and RTL checks, actual
whole-system resource/timing checks and board HDMI tests. Keep the current
accepted V173 release and V179 experiment intact throughout.
