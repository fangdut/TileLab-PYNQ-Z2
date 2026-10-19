"""Verify candidate source/artifact integrity, without contacting a board."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json
R=Path(__file__).resolve().parents[1]

def verify(root=R):
    root=Path(root).resolve();manifest=root/'CANDIDATE_MANIFEST.json'
    data=json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('firmware_version')!=0x12c00 or data.get('status')!='research_candidate':
        raise ValueError('Not the expected research candidate manifest')
    required={'rtl/directional_mean_valley.v','rtl/mean_dual_scale_valley.v','rtl/video_bypass.v',
              'reports/v154/download/system.bit','reports/v154/download/system.xsa',
              'reports/v154/download/hdmi_ethernet/build/hdmi_ethernet.elf','reports/v154/download/ps7_init.tcl'}
    if not required.issubset(data['files']):raise ValueError('Manifest omits required candidate files')
    for name,digest in data['files'].items():
        rel=PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:raise ValueError('Unsafe manifest path')
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file():raise ValueError('Missing or linked-out candidate file: '+name)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Candidate hash mismatch: '+name)
    return data,hashlib.sha256(manifest.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=R);ap.add_argument('--require-board',action='store_true');args=ap.parse_args()
    data,digest=verify(args.root)
    result=dict(integrity_valid=True,files_checked=len(data['files']),manifest_sha256=digest,
                hardware_implemented=data.get('hardware_implemented',False),
                new_board_acceptance=False,industrial_validation=False)
    print(json.dumps(result))
    if args.require_board:raise SystemExit('Candidate has not completed new board acceptance; historical V1.53 evidence is insufficient')
if __name__=='__main__':main()
