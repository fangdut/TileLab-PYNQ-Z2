"""Derive startup gains from an independent captured black/white pattern.

Offline calibration only. No photo labels, threshold changes, or runtime pixels.
"""
from pathlib import Path
import argparse, hashlib, json, zlib
import numpy as np


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    for key in ['snapshot', 'model', 'out']:
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('Use a fresh profile file')
    evidence_path = a.snapshot / 'evidence.json'
    proof = json.loads(evidence_path.read_text())
    if proof['scope'] != 'PAUSED_PHYSICAL_HDMI_INPUT_AND_PL_RESULT' or not proof['arm_cores_halted_during_dump']:
        raise ValueError('Physical paused-frame proof required')
    if proof.get('video_register_version') == 0x17200001 and proof.get('color_registers') != [256,256,256,1]:
        raise ValueError('Measure the independent ramp with identity color settings first')
    raw = (a.snapshot / 'rgb.bin').read_bytes()
    if len(raw) != 720*720*4 or sha(a.snapshot/'rgb.bin') != proof['files']['rgb.bin'] or zlib.crc32(raw) != proof['rgb_crc32']:
        raise ValueError('Calibration frame identity failed')
    words = np.frombuffer(raw, dtype='<u4').reshape(720, 720)
    rgb = np.stack(((words >> 16)&255, (words >> 8)&255, words&255), axis=-1).astype('i4')
    # Match the input generator's fixed gray ramp: black x<104, white x>=616.
    # Stay away from transitions, frame edges and any text outside the ROI.
    black = np.median(rgb[100:620, 20:80], axis=(0, 1)).astype('i4')
    white = np.median(rgb[100:620, 640:700], axis=(0, 1)).astype('i4')
    span = white-black
    if np.any(span < 64):
        raise ValueError('Insufficient black/white span')
    for roi, center in [(rgb[100:620, 20:80], black), (rgb[100:620, 640:700], white)]:
        if np.quantile(np.abs(roi-center), .99) > 2:
            raise ValueError('Expected independent constant calibration patches')
    line = np.median(rgb[100:620, 104:616], axis=0)
    if np.any(np.diff(line, axis=0) < -2):
        raise ValueError('Expected monotone calibration ramp')
    gain = (255*256+span//2)//span
    if np.any(gain > 1023):
        raise ValueError('Gain exceeds hardware range')
    expected = np.arange(512)//2
    corrected = np.clip((line.astype('i4')*gain+128)>>8,0,255)
    residual = np.abs(corrected-expected[:,None])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    result = dict(scope='INDEPENDENT_HDMI_BLACK_WHITE_STARTUP_CALIBRATION',
        model_sha256=sha(a.model), black_rgb=black.tolist(), white_rgb=white.tolist(),
        gain_q8_rgb=gain.tolist(), calibration_evidence_path=str(evidence_path.resolve()),
        independent_gray_levels=256,corrected_gray_channel_mae=residual.mean(axis=0).tolist(),
        corrected_gray_channel_max_error=residual.max(axis=0).tolist(),
        calibration_evidence_sha256=sha(evidence_path), calibration_frame_sha256=sha(a.snapshot/'rgb.bin'),
        calibration_source='RealPhotoSource independent gray ramp; no tile photo or defect labels used',
        runtime_arithmetic='PL saturate(round(max(pixel-black,0)*gain_q8/256))',
        limitations='Fixed HDMI source/display profile. Recalibrate after source color settings change; not a camera color-constancy model.')
    a.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
