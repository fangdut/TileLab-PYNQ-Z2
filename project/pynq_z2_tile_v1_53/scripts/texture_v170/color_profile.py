"""Validate a startup-only HDMI color profile; never process image pixels."""
from pathlib import Path
import hashlib, json


def load_profile(path, model_sha256):
    data = json.loads(path.read_text())
    if data.get('scope') != 'INDEPENDENT_HDMI_BLACK_WHITE_STARTUP_CALIBRATION':
        raise ValueError('Independent startup color calibration required')
    if data.get('model_sha256') != model_sha256:
        raise ValueError('Color profile bound to another model')
    for key, low, high in [('black_rgb', 0, 255), ('gain_q8_rgb', 1, 1023)]:
        values = data.get(key)
        if not isinstance(values, list) or len(values) != 3 or any(
                type(v) is not int or not low <= v <= high for v in values):
            raise ValueError('Invalid ' + key)
    evidence = Path(data['calibration_evidence_path'])
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    if digest != data['calibration_evidence_sha256']:
        raise ValueError('Independent calibration evidence changed')
    proof = json.loads(evidence.read_text())
    if proof.get('scope') != 'PAUSED_PHYSICAL_HDMI_INPUT_AND_PL_RESULT':
        raise ValueError('Physical calibration frame evidence required')
    if not proof.get('arm_cores_halted_during_dump'):
        raise ValueError('Calibration dump has no ARM halt proof')
    if proof['files']['rgb.bin'] != data['calibration_frame_sha256']:
        raise ValueError('Calibration frame provenance mismatch')
    return dict(profile_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                black_rgb=data['black_rgb'], gain_q8_rgb=data['gain_q8_rgb'],
                register_words=[(b << 16) | g for b, g in zip(
                    data['black_rgb'], data['gain_q8_rgb'])],
                calibration_evidence_sha256=digest,
                calibration_frame_sha256=data['calibration_frame_sha256'],
                calibration_source=data['calibration_source'],
                runtime_pixel_processing='FPGA fabric only')
