# FPGA engineering status — 2026-10-20

The frozen V170 HLS11 implementation physically processed all 117 original MVTec Tile development photos on PYNQ-Z2: 84/84 anomalies including 17/17 cracks, 0/33 normal false alarms. Every integer score and original-size mask matched the frozen reference exactly. This benchmark was repeatedly used for development and is not independent validation.

Actual PL auto-restart measured 27 completed frames in 10.0179 seconds: **2.695 FPS**, with one ARM start. Single-image core mean is 0.3715 seconds. The first integer implementation measured 1.555 FPS; the earlier full FP32 baseline took about 553 seconds per image. None is claimed to meet the first 10 FPS target. Fixed-frame DDR replay, Ethernet transfers and continuous HDMI are different measurements.

PL computes the full detector. PC decodes, packs, transports and renders; ARM handles transport/CRC/control/timing. There is no CPU/GPU detection fallback. The frozen runtime is deliverables/V170_Verified_FullPL_2p70FPS_R2.zip; the package was CRC/SHA checked and recreated unit vectors are byte-exact with the verified build. Source/model/BIT/XSA/ELF/results are bound in project/pynq_z2_tile_v1_53/reports/v170/verification.json.

Current HLS source is the next experimental dataflow implementation. HLS15 preserves all 117 outputs in C++ and passed strengthened two-launch RTL tests, including intermediate CNN tensors and FIFO backpressure. The first failed RTL attempt was not programmed. A complete HLS15 hardware implementation is in progress; its board speed is not established. Use the frozen ZIP or frozen/v170_hls11.cpp for the verified version. Do not confuse current experiments with the passed snapshot.

Camera/video scaffolding in experimental/video_v171 has standalone RTL tests for scheduler, DDR write ownership/CRC/length, ROI, async FIFO and pixel reset recovery. It is not yet integrated on-board with HDMI.

Image-level results do not establish pixel tracing: historical abnormal-mask mean IoU is about 0.519, crack mean IoU about 0.067. Crack localization remains coarse. Arbitrary painted/mixed materials, continuous video, independent physical validation and competition final acceptance remain open. Original code is MIT; MVTec-derived data/model/evidence retain CC BY-NC-SA 4.0 and upstream IP/weights keep their terms.
