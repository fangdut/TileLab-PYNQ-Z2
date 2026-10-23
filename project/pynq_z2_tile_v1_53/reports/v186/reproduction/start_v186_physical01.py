"""Only after source-bound full RTL passes, try the measured control-path fix."""
from pathlib import Path
import json,subprocess,time,sys
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
deadline=time.monotonic()+7200
while True:
    j=json.loads((W/'v186_hls71_full_pipeline.json').read_text())
    if j['status']=='FAILED_NO_PROMOTION':raise RuntimeError('Full HLS71 failed; no physical build or programming')
    if j['status'].startswith('SKIPPED_'):raise RuntimeError('Full HLS71 skipped; review current accepted board result')
    if j['status']=='RTL_IP_FINISHED_NEEDS_PHYSICAL_AND_BOARD':break
    if time.monotonic()>deadline:raise TimeoutError('Full RTL not ready; no new physical job')
    time.sleep(10)
args=[sys.executable,'-X','utf8',P/'scripts/texture_v170/run_physical_trial.py',
 '--hls',W/'v170_hls71','--regression',W/'v186_all_c01','--profile',W/'v170_fullint224',
 '--dataset',W/'dataset_v168','--catalog',W/'v171_source01/catalog_all117.json',
 '--player',W/'RealPhotoSource_v171_r7.exe','--hardware',W/'v186_hw01','--run',W/'v186_acceptance01',
 '--journal',W/'v186_physical_pipeline01.json','--video-rtl-gate',W/'v183_rtl_gate01.json',
 '--clock-mhz','125','--memory-layout','split','--ip-cache',W/'v185_hw01/ip_cache',
 '--label','V186 Split Normalization Cache 125MHz','--render-baseline',W/'v172_uncorrected_series02',
 '--render-previous',W/'v179_acceptance01','--max-repair-deficit-ns','0.5']
raise SystemExit(subprocess.run([str(x) for x in args]).returncode)
