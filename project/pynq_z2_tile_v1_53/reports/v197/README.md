# V197 source and experiment evidence

Author checkpoint on author data is a reproduction, NOT independent validation.
Original256x1408 scans: float and integer reference40TP/0FP on80files. The full
new detector has NOT been built as FPGA hardware or run on the board.
Only the integer InstanceNorm unit is in HLS/RTL validation; inspect status.html
for actual completion, not a projected result. No training or GPU deployment.

HFENet source code Copyright2021RobotvisionLab, MIT. The unmodified module and
license are preserved in experimental/hfenet_v197/vendor. Checkpoint/source URLs
and Git/SHA256 identities are pinned. Source/checkpoint original upstream:
https://github.com/RobotvisionLab/HFENet/tree/6edf57293da051a5d9d2164482f88b68ef45c11f

HFENet raw photos, labels, predicted raster masks, fitted reference binaries,
normalization moments/activation samples and checkpoint/quantized weight binaries
are kept locally and not distributed here. Software MIT does not imply a dataset
license. Local review gallery is separate. Numeric protocols, confusion results,
synthetic arithmetic fixtures and code are preserved, including failed trials.
Prior MVTec station images/derivatives retain CC BY-NC-SA4.0 and attribution.
Original TileLab source is MIT; AMD/vendor artifacts retain their own terms.
