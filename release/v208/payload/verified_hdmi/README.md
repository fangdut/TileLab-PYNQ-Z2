# Verified FPGA video development snapshot

Actual HDMI input: 117/117 exposed MVTec Tile development photos correct, 0/33 normal false alarms, 84/84 anomalies and 17/17 cracks detected. FPGA completed 1957 autonomous detections over 239.548 seconds (8.169553 FPS). Both ARM cores were checked halted 119 times; no CPU/GPU detection or CPU per-frame start writes. Fixed-frame speed: 8.021126 FPS.

This is not a final competition submission. Independent blind accuracy, arbitrary painted/mixed materials, precise crack tracing and sustained 10 FPS remain open. Input photos are original publicly sourced MVTec photographs, displayed through HDMI; this is not evidence of a new camera or a complete physical tile installation.

Open report.html. hardware/ contains the exact programmed BIT/XSA; software/ the matching transport ELF; model/ the frozen model. evidence/all117_direct_raw.zip preserves every full board output. Source/model/artifact hashes are in PACKAGE_MANIFEST.json. The recorded boot 1363500809 belongs to this experiment; reruns need fresh programming and validation records.

Full project and vendor IP dependencies: https://github.com/fangdut/TileLab-PYNQ-Z2/tree/43e52652bc7e9ef6cfa4aadf5b1bdbeb8654c4a2 . The exact accepted HLS source is source/texture_integer.cpp; hls/accepted_export.zip and unit_vectors/ match it. Video variant: overlap_v175; its compiled RTL sources are in source/experimental/video_overlap_v175/rtl. hardware/candidate_preflight.json records the actual source-bound build selection. Later experimental kernels in the repository are separate. Rebuilding the complete Vivado project requires that pinned repository and AMD tools 2025.2; this archive contains compiled artifacts and supporting sources.

From the extracted package root, volatile JTAG programming is supported with:
python source/scripts/texture_v170/program_board.py --hardware hardware --software software --out runtime/program_new

Use a fresh output folder. PC Ethernet: 192.168.33.30/24; board: 192.168.33.10:9136. Runtime file transport uses numpy/Pillow; Torch is only needed for optional offline reference audits. HDMI inference and color correction run in PL. Recalibrate from an independent gray ramp after changing the HDMI source color settings; archived color_profile.json records this experiment only. No Flash programming is performed.

Original code is MIT. MVTec-derived photos/models/evidence retain CC BY-NC-SA 4.0; AMD/Xilinx/Digilent and other upstream components retain their licenses.
