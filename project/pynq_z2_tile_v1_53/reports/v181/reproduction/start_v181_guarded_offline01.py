"""One offline C regression; wait for the active board trial before any HLS."""
from pathlib import Path
import ctypes,json,subprocess,sys,time,hashlib
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53')
state=W/'v181_offline_pipeline01.json';assert not state.exists()
j=dict(scope='SOURCE_BOUND_RESIDUAL_OFFLINE_EXPERIMENT_NOT_BOARD',status='FULL_C_STARTED',board_programmed=False)
def save():state.write_text(json.dumps(j,indent=2)+'\n')
try:
    save();r=subprocess.run([sys.executable,'-X','utf8',str(W/'start_v181_residual_full_c.py')]);assert r.returncode==0
    summary=json.loads((W/'v181_all_c01/summary.json').read_text());assert summary['cases']==summary['correct']==117 and summary['all_grid_values_exact'] and summary['all_original_size_masks_exact']
    assert summary['source_sha256']==hashlib.sha256((P/'experimental/texture_v170/hls/frozen/v170_hls63.cpp').read_bytes()).hexdigest()
    j.update(status='C_EXACT_WAIT_ACTIVE_PHYSICAL_EXPERIMENT');save();deadline=time.monotonic()+5400
    while True:
        active=json.loads((W/'v180_physical_pipeline01.json').read_text())
        if active['status'] in ['EXPERIMENT_COMPLETE_REVIEW_ACTUAL_SPEED_BEFORE_PROMOTION','FAILED_NO_PROMOTION']:break
        if time.monotonic()>deadline:raise TimeoutError('Active physical experiment not finished; no HLS launched')
        time.sleep(10)
    if active.get('board_result_review',{}).get('ten_fps_over_complete_series'):
        j.update(status='C_EXACT_OPTIONAL_SYNTH_DEFERRED_TEN_FPS_MILESTONE_REACHED');save()
    else:
        j.update(status='SYNTHESIS_ONLY_STARTED');save()
        r=subprocess.run([sys.executable,'-X','utf8',str(W/'start_v181_hls63_synth.py')]);assert r.returncode==0
        j.update(status='C_AND_SYNTH_FINISHED_REQUIRES_RTL_AND_PHYSICAL_VALIDATION');save()
except Exception as e:j.update(status='FAILED_NO_PROMOTION',error=str(e));save();raise
print(json.dumps(j),flush=True)
