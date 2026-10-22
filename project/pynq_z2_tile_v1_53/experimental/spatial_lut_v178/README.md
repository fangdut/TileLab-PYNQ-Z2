# V178 spatial-coordinate hardware candidate — not board accepted

V176 HW03's125MHz routed design fails setup around-1.57ns. Its worst path runs
through a constant-division reciprocal multiplier into the spatial-address DSP
C input. The automatic single physical repair remains a separate bounded trial.

HLS55 derives from HLS53, keeping the original32-position DW schedule for an
isolated timing comparison. A two-stage16-word coordinate ROM replaces tap/9,
tap%9 and tap/3/tap%3 in the3x3 spatial address generator. Actual model descriptor
inspection finds only one standard3x3 layer, the first RGB layer (ic3); all other
3x3 layers are depthwise. For standard3x3 with at most8 input channels, there is
only one8-channel input group, so its input-group index is alwayszero and the
nine taps map exactly to the3x3 row/column raster.

This explicitly specializes the supported model graph. A runtime guard rejects
standard3x3 input channels above8 rather than silently using the wrong address.
check_spatial_coordinates.py verifies the actual binary descriptors against
graph.json, the model SHA/CRC, every kernel coordinate and the runtime guard.
build_candidate.py requires that proof whenever this source variant is used.
test_model_guard.py rejects both an injected ic16 standard3x3 descriptor and a
model/graph mismatch. Existing1x1 stride handling and nearest-codebook indexing
remain unchanged. Model weights and threshold10908 are frozen.

Full117 original-photo C regression and an8ns-target HLS synthesis are running.
No full RTL, actual implementation frequency or board throughput exists yet.
Do not infer an achieved125MHz clock from this algorithm-preserving proposal.
