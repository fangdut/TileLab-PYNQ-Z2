"""Wait for the one full RTL job, then attempt source-bound 100MHz hardware."""
from pathlib import Path
import subprocess,time,json,sys
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
deadline=time.monotonic()+2400
while True:
    j=json.loads((W/'v179_hls62_full_pipeline.json').read_text())
    if j['status']=='FAILED_NO_PROMOTION':raise RuntimeError('HLS62 failed; no physical build or programming')
    if j['status']=='RTL_IP_FINISHED_NEEDS_PHYSICAL_AND_BOARD':break
    if time.monotonic()>deadline:raise TimeoutError('RTL not ready; no physical build launched')
    time.sleep(10)
args=[sys.executable,'-X','utf8',P/'scripts/texture_v170/run_physical_trial.py',
 '--hls',W/'v170_hls62','--regression',W/'v179_all_c05','--profile',W/'v170_fullint224',
 '--dataset',W/'dataset_v168','--catalog',W/'v171_source01/catalog_all117.json',
 '--player',W/'RealPhotoSource_v171_r7.exe','--hardware',W/'v179_hw01','--run',W/'v179_acceptance01',
 '--journal',W/'v179_physical_pipeline01.json','--video-rtl-gate',W/'v176_rtl_gate04.json',
 '--clock-mhz','100','--ip-cache',W/'v176_hw03/ip_cache','--label','V179',
 '--render-baseline',W/'v172_uncorrected_series02','--render-previous',W/'v173_acceptance08',
 '--max-repair-deficit-ns','0.5']
r=subprocess.run([str(x) for x in args]);raise SystemExit(r.returncode)
