"""Verify candidate source/artifact integrity, without contacting a board."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,zipfile
R=Path(__file__).resolve().parents[1]

def verify(root=R):
    root=Path(root).resolve();manifest=root/'CANDIDATE_V155_MANIFEST.json'
    data=json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('firmware_version')!=0x12d00 or data.get('status')!='research_candidate':
        raise ValueError('Not the expected research candidate manifest')
    required={'rtl/directional_mean_valley.v','rtl/mean_dual_scale_valley.v','rtl/wide_line_window_v155.v','rtl/wide_line_dual_valley_v155.v','rtl/raster_directional_v155.v','models/support_profiles_v155.py','reports/v155/FINAL_PROFILE.json','rtl/video_bypass.v',
              'reports/v155/download/system.bit','reports/v155/download/system.xsa',
              'reports/v155/download/hdmi_ethernet/build/hdmi_ethernet.elf','reports/v155/download/ps7_init.tcl'}
    if not required.issubset(data['files']):raise ValueError('Manifest omits required candidate files')
    for name,digest in data['files'].items():
        rel=PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:raise ValueError('Unsafe manifest path')
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file():raise ValueError('Missing or linked-out candidate file: '+name)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Candidate hash mismatch: '+name)
    if data.get('hardware_implemented'):
        with zipfile.ZipFile(root/'reports/v155/download/system.xsa') as archive:
            bits=[name for name in archive.namelist() if name.endswith('.bit')]
            if len(bits)!=1 or hashlib.sha256(archive.read(bits[0])).hexdigest()!=data['files']['reports/v155/download/system.bit']:
                raise ValueError('XSA embedded BIT and selected standalone BIT mismatch')
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

