# FPGA engineering status — 2026-10-20

Latest physically verified: V170 HLS15 / HW05 / SW07, boot 1348147017. PYNQ-Z2 processed all 117 original MVTec Tile development photos: 84/84 anomalies including 17/17 cracks; 0/33 normal false alarms. All integer scores and original-size masks exactly match the frozen reference. These repeatedly exposed images are a development benchmark, not independent validation.

Measured fixed-frame PL auto-restart: 33 frames in 7.711191 seconds = **4.279494 FPS**, one ARM start. Mean single-image core time 0.233733 seconds. Earlier HLS11 measured 2.695 FPS and the FP32 baseline about 553 seconds per image. No build is yet accepted at the first 10 FPS target or as continuous HDMI video.

The complete reproducible verified package is deliverables/V170_Verified_FullPL_4p28FPS_R1.zip, SHA256 8e50561cf2779efe76d33e14d37b3df7bfa901a6f98240f38a6dbc813cf421bc. Manifest hashes, ZIP CRC, actual unit vectors and frozen source were checked. reports/v170/hls15_verified binds source/model/BIT/XSA/ELF/physical results. Earlier verified snapshots remain preserved.

Runtime PL performs resize, normalization, CNN, pooling, projection, normal-codebook distance search, smoothing, alarm and mask. PC decodes/transports/displays; ARM transports/CRC/configures/times. No CPU/GPU detection fallback. All board programming is volatile JTAG, not Flash.

Current HLS source is experimental HLS19: explicit DDR row bursts/cache, following HLS18's common 128-DSP convolution/distance engine. HLS18 passed two-launch RTL/CNN feature checks using 213 DSP. It has not yet passed physical validation. Use hls/frozen/v170_hls15.cpp or the verified ZIP for the accepted snapshot.

The HDMI chain includes native ROI acquisition, async FIFO, DDR commit after write responses, PL HLS scheduling, header/sequence verification and a whole-tile alarm border. Three-frame integrated bus-model simulation passed; this is not CNN or on-board video proof. The first integrated HLS15 build failed timing and was not programmed. A BRAM-accumulator HLS18 build is underway. Control addresses are explicitly mapped for both PS and the PL master; no reliance on auto-assigned aliases.

Image decisions do not establish crack tracing: historical abnormal-mask mean IoU approximately 0.519, crack mean IoU approximately 0.067. Arbitrary painted/mixed materials, independent physical validation, continuous-video throughput and competition final acceptance remain open. Original code is MIT; MVTec-derived data/models/evidence retain CC BY-NC-SA 4.0, with vendor/upstream terms preserved.
