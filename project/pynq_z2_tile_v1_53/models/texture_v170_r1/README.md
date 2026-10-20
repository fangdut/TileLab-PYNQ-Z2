# V170 integer deployment candidate

This frozen candidate uses MobileNetV2 features 0-13, 224x224 input, PCA64 and 1024 normal codewords. All detection arithmetic is integer: rational bilinear preprocessing, INT8 CNN, INT16 projection/codebook, integer distances, smoothing, threshold and mask. model.bin is the exact hardware ABI and its SHA256/CRC32 are in graph.json. Python/Torch scripts are OFFLINE design/calibration tools, not a runtime fallback.

The exposed historical MVTec Tile development benchmark gives 84/84 anomalies detected (17/17 cracks), 0/33 normal false alarms. Architecture choices were compared on this benchmark; it is not independent validation, not a general material claim and not a board accuracy measurement. Normal-only memory fitting and calibration IDs are frozen in protocol.json. New-board validation remains pending.

MVTec-derived profiles/model/head/scores/results retain CC BY-NC-SA 4.0; do not treat these artifacts as MIT. Official Torch checkpoint: https://download.pytorch.org/models/mobilenet_v2-7ebf99e0.pth ; original pretrained-weight terms apply. Normal source SHA/provenance is in dataset_manifest.json.
