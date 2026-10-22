"""Synthetic metadata control-flow tests; never a physical speed result."""
from pathlib import Path
import json,sys,copy,ast,hashlib,argparse
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
sys.path.insert(0,str(P/'scripts/texture_v170'));from run_physical_trial import review_board_result
parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=W/'v180_target_flag_checks01');args=parser.parse_args()
out=args.out;out.mkdir(exist_ok=False);relative=['progress.json','board117/summary.json','hdmi117/summary.json']
source={n:json.loads((W/'v179_acceptance01'/n).read_text()) for n in relative};results=[]
for case,valid in [('synthetic_consistent_target',True),('synthetic_false_target_claim',False)]:
    docs=copy.deepcopy(source);docs['progress.json']['status']='DEVELOPMENT_ACCURACY_AND_TEN_FPS_PASS'
    if valid:
        d=docs['hdmi117/summary.json'];d['autonomous_frames_in_interval']=2448;d['continuous_observation_seconds']=240.;d['autonomous_hdmi_fps_over_photo_series']=10.2
    root=out/case
    for n,v in docs.items():p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v))
    try:
        review=review_board_result(root)
        if not valid:raise AssertionError('False target claim accepted')
        assert review['ten_fps_over_complete_series'];results.append(dict(case=case,expected_outcome='accepted synthetic control-flow fixture',passed=True))
    except ValueError as e:
        if valid:raise
        results.append(dict(case=case,expected_outcome='rejected inconsistent synthetic target claim',passed=True,error=str(e)))
paths=[P/('scripts/texture_v170/'+n) for n in ['accept_video_candidate.py','run_physical_trial.py','package_verified_video.py']]+[P/'tools/fpga_texture_v170/render_video_report.py']
for p in paths:ast.parse(p.read_text(encoding='utf8'))
j=dict(scope='SYNTHETIC_TARGET_STATUS_TEST_NOT_HARDWARE_OR_TEN_FPS_EVIDENCE',passed=True,tests=results,source_hashes={str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
