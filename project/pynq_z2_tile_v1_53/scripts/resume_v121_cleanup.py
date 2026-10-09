"""Resume a completed four-case diagnostic whose player failed during cleanup.
Preserve the original failure and case evidence; do not relabel the first run.
"""
from pathlib import Path
import json,sys
from board_v121_dma_recovery import R,W,O,wait_idle,source,execute,ready,action,dump
out=O/sys.argv[1]
if out.resolve().parent!=O.resolve():raise ValueError('Unexpected evidence directory')
cases=[json.loads((out/f'case_{i}/result.json').read_text(encoding='utf-8')) for i in range(1,5)]
assert all(c['passed'] and c['independent_process_reload_passed'] for c in cases)
original=(R/'reports/v132/dma_recovery_board_console.log').read_text(encoding='utf-8-sig')
assert 'TimeoutError: Background acceptance condition not reached' in original
(out/'original_cleanup_failure.log').write_text(original,encoding='utf-8')
lock=json.loads((R/'reports/v132/player_lock.json').read_text(encoding='utf-8-sig'));assert lock['passed']
wait_idle();source('station_6')
execute(['cmd.exe','/d','/c',str(W/'program_ethernet.bat')],out/'resumed_restore.log')
clean=ready(out/'resumed_clean_ready.json');assert clean['capture_recovery']['attempts']==0
action('display',value='real_video');action('start')
result=dict(passed=True,cases=cases,clean_restart=clean,run_directory=str(out),
 cleanup_resumed=dict(original_failed=True,reason='WPF player command-file sharing violation terminated HDMI stimulus before clean reload',failure_log=str(out/'original_cleanup_failure.log'),player_lock_validation=lock,resumed_successfully=True),
 scope='Four actual release DMA halt cases passed before cleanup failure; player fixed and exclusive-lock tested, then clean programming resumed. No physical HDMI unplug or power-loss claim.')
dump(O/'summary.json',result);dump(O/'stage.json',dict(stage='complete_after_cleanup_repair',run_directory=str(out)))
print(json.dumps(dict(passed=True,cases=4,clean_boot=clean['boot_id'],cleanup_resumed=True)))
