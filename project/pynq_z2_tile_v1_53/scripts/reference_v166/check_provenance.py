"""Check saved evidence integrity, never substitute it for real accuracy."""
from pathlib import Path
import hashlib,io,json,sys,zipfile
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/reference_tile'))
import reference_v166 as detector
from reference_tile import sha,canonical

def main():
    out=ROOT/'reports/v166';protocol=json.loads((out/'FINAL_PROTOCOL.json').read_text());vectors=json.loads((out/'pixel_vectors/manifest.json').read_text());proof=json.loads((out/'METRIC_BOARD_PROOF.json').read_text());board=json.loads((out/'BOARD_REPLAY.json').read_text());binding=json.loads((out/'BOARD_REPLAY_BINDING.json').read_text())
    if protocol['implementation']!=detector.implementation() or protocol['policy']!=detector.policy():raise ValueError('Executed reference implementation/policy changed')
    for name,digest in protocol['source_sha256'].items():
        if sha(ROOT/'tools/reference_tile'/name)!=digest:raise ValueError('Executed audit dependency changed: '+name)
    for name,digest in vectors['sha256'].items():
        if sha(out/'pixel_vectors'/name)!=digest:raise ValueError('Vector changed')
    if vectors['rtl_sha256']!=sha(ROOT/'experimental/reference_v166/rtl/reference_metric_v166.v') or vectors['testbench_sha256']!=sha(ROOT/'sim/tb_reference_metric_v166.sv'):raise ValueError('Simulated RTL/testbench changed')
    if vectors['generator_sha256']!=sha(ROOT/'scripts/reference_v166/prepare_metric_vectors.py'):raise ValueError('Arithmetic oracle/generator changed')
    if 'PASS 8192 exact' not in (out/'rtl_passed.txt').read_text():raise ValueError('Missing simulation proof')
    if proof['rtl_sha256']!=vectors['rtl_sha256'] or proof['bist_sha256']!=sha(ROOT/'experimental/reference_v166/rtl/reference_metric_bist_v166.v'):raise ValueError('Board arithmetic source mismatch')
    if proof['hardware_readback_passed'] is not True:raise ValueError('Hardware result has not passed')
    for name,digest in proof['source_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Executed board test helper changed')
    release=ROOT/'releases/v166_metric_bist'
    if sha(release/'bist_wrapper.bit')!=proof['bit_sha256'] or sha(release/'metric_bist.ltx')!=proof['ltx_sha256']:raise ValueError('Tested arithmetic image mismatch')
    lines=(out/'metric_readback.txt').read_text().splitlines();trials=[line for line in lines if line.startswith('TRIAL ')]
    if len(trials)!=3 or not any(line.startswith('PASS ') for line in lines):raise ValueError('Hardware result is incomplete')
    for line in trials:
        value=int(line.split()[2],16)
        if value>>48!=0x166b or (value>>45)&7!=4 or (value>>33)&4095!=2048 or (value>>21)&4095!=2048 or (value>>8)&8191:raise ValueError('Hardware result failed')
    for name,digest in binding['source_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Captured-pixel reference/bridge changed')
    if sha(out/'board_captures.zip')!=binding['archive_sha256'] or len(board['rows'])!=50 or not board['hardware_consistency_passed']:raise ValueError('Missing board replay evidence')
    with zipfile.ZipFile(out/'board_captures.zip') as z:
        if len(z.namelist())!=200:raise ValueError('Unexpected board evidence members')
        for row in board['rows']:
            image=z.read(row['source']+'/original.png');mask=z.read(row['source']+'/pl_mask.png')
            if hashlib.sha256(image).hexdigest()!=row['captured_sha256'] or hashlib.sha256(mask).hexdigest()!=row['mask_sha256']:raise ValueError('Captured evidence SHA mismatch')
            with Image.open(io.BytesIO(image)) as im:
                if im.size!=(1280,720) or im.mode!='RGB':raise ValueError('Capture dimensions/mode changed')
            with Image.open(io.BytesIO(mask)) as im:a=np.array(im)
            if a.shape!=(720,1280) or set(np.unique(a))-{0,255} or int((a>0).sum())!=row['hardware']['candidate_pixels']:raise ValueError('PL mask snapshot changed')
            if row['mask_mismatch_pixels']!=0 or not row['arithmetic_and_transport_passed']:raise ValueError('Recorded PL arithmetic failed')
    print(json.dumps(dict(saved_board_evidence_integrity=True,pl_replay_images=50,hardware_unique_metric_windows=2048,hardware_runs=3,rtl_vectors=8192,accuracy_qualified=False,reference_video_integrated=False)))

if __name__=='__main__':main()
