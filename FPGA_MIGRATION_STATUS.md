# FPGA migration — engineering status, 2026-10-20

The V169 full PL baseline has physically passed two real-photo normal/crack numerical checks on PYNQ-Z2. PL performs resize, normalization, the entire CNN, PCA, normal-codebook search, smoothing, alarm and mask. ARM performs transport/CRC/control; PC performs file decoding, transport and rendering. There is no CPU/GPU vision fallback. The old CPU-only station was stopped.

**V169 is not realtime:** measured PL time is 552.607 s/image. These two cases do not establish 117-image board accuracy or competition acceptance. Read `project/pynq_z2_tile_v1_53/reports/v169/acceptance.json` and `board_summary.json`. The compiled ZIP holds the matching timing-closed bitstream, XSA, ELF, HLS IP and source proof. Rebuild its exact 100 MB model with `tools/fpga_texture_v169/rebuild_model.py`; frozen profile is in `models/texture_v169_r1`. Full local package also contains model.bin.

**V170 is the realtime candidate, not yet accepted on board.** A lightweight fully integer network reduces CNN MACs 175x (36.75G to 209.86M), and model bytes from 100,038,912 to 751,760. The exposed historical development set yields 117/117 correct after integer preprocessing and integer scoring; model selection used this benchmark, so this is not blind generalization evidence. All 117 real-photo HLS C++ score grids and original-size masks match the frozen integer reference exactly; see reports/v170/full_c_summary.json. HLS implementation/resource/timing optimization and physical verification are ongoing. No FPGA FPS claim yet.

Target: at least 10 sustained detections/s as a first milestone, then faster. Ethernet file-transfer throughput, kernel throughput and continuous video throughput must be reported separately. HDMI continuous input and a PL-owned frame scheduler are still required before claiming a standalone realtime video detector. ARM must not perform detection. Painted/mixed materials outside this tile material remain unvalidated.

Original project code is MIT. MVTec-derived data, model profiles and real-photo evidence retain CC BY-NC-SA 4.0; upstream IP/weights keep their original terms. See LICENSE_SCOPE.md.
