"""One source-identical DDR topology/frequency trial after V179 is verified."""
from pathlib import Path
import json,hashlib,subprocess,sys
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
verified=json.loads((P/'reports/v179/verified_hdmi_overlap/verification.json').read_text())
assert verified['cases']==117 and verified['normal_false_alarms']==0 and verified['continuous_hdmi_fps']>verified['previous_v173_r2_hdmi_fps']
assert verified['kernel_sha256']==hashlib.sha256((W/'v170_hls62/src/texture_integer.cpp').read_bytes()).hexdigest()
assert verified['model_sha256']=='1501e32e733b566e17d125613d0989c04291b658459d63b826e418f6f713ed65'
assert verified['memory_layout_proof']['memory_layout']=='shared'
args=[sys.executable,'-X','utf8',P/'scripts/texture_v170/run_physical_trial.py',
 '--hls',W/'v170_hls62','--regression',W/'v179_all_c05','--profile',W/'v170_fullint224',
 '--dataset',W/'dataset_v168','--catalog',W/'v171_source01/catalog_all117.json',
 '--player',W/'RealPhotoSource_v171_r7.exe','--hardware',W/'v180_hw01','--run',W/'v180_acceptance01',
 '--journal',W/'v180_physical_pipeline01.json','--video-rtl-gate',W/'v176_rtl_gate04.json',
 '--clock-mhz','125','--memory-layout','split','--ip-cache',W/'v179_hw01/ip_cache',
 '--label','V180 DDR Split 125MHz','--render-baseline',W/'v172_uncorrected_series02',
 '--render-previous',W/'v179_acceptance01','--max-repair-deficit-ns','0.5']
raise SystemExit(subprocess.run([str(x) for x in args]).returncode)
