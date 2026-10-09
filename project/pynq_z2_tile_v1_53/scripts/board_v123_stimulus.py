"""Real workstation/WPF/board with deliberate Windows file sharing conflicts.

The board and acquired images are never replaced by simulated protocol data.
"""
from pathlib import Path
import ctypes,json,sys,time,urllib.request,os
from ctypes import wintypes
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/stimulus_board';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'scripts'))
from board_v18_continuous import action,state

kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
kernel.CreateFileW.restype=wintypes.HANDLE;kernel.CloseHandle.argtypes=[wintypes.HANDLE]

class FileHold:
 def __init__(self,name,share):self.path=R/'host'/name;self.share=share;self.handle=None
 def __enter__(self):
  self.handle=kernel.CreateFileW(str(self.path),0x80000000,self.share,None,3,0,None)
  if self.handle==wintypes.HANDLE(-1).value:raise ctypes.WinError(ctypes.get_last_error())
  return self
 def __exit__(self,*args):kernel.CloseHandle(self.handle)

def dump(name,value):(O/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def until(fn,seconds=10):
 end=time.monotonic()+seconds
 while True:
  s=state()
  if fn(s):return s
  if time.monotonic()>end:raise TimeoutError('Stimulus condition not reached: '+json.dumps(s['stimulus_status'],ensure_ascii=False))
  time.sleep(.08)
def healthy(s):
 assert s['revision']=='V1.23' and not s['error'] and s['enabled'] and s['board_connected']
 assert s['capture_health']['ready'] and not s['capture_health']['stale']
 assert s['board_stats']['version']==0x11700
def sample_for(seconds,expected):
 rows=[];begin=time.monotonic()
 while time.monotonic()-begin<seconds:
  s=state();healthy(s);assert s['stimulus_status']['state'] in expected
  rows.append(dict(seconds=time.monotonic()-begin,state=s));time.sleep(.1)
 return rows
def ui_checkpoint(name):
 if '--ui' not in sys.argv:return
 token=O/(name+'_continue_'+str(time.time_ns()))
 dump(name+'_ready.json',dict(continue_file=str(token),state=state()))
 print('UI CHECKPOINT '+name,flush=True);end=time.monotonic()+45
 while not token.exists():
  if time.monotonic()>end:raise TimeoutError('UI checkpoint expired: '+name)
  time.sleep(.1)

def run():
 before=None;proof=dict(passed=False,scope='Actual HTTP API, WPF player and HDMI/FPGA board; Windows sharing conflicts on command and telemetry files')
 try:
  action('storage',mode='preview',max_archive_mib=1024);action('display',value='real_video');action('start')
  before=until(lambda s:s['stimulus_status']['ready'] and s['stimulus_status']['observed']=='real_video' and s['board_connected'] and s['capture_health'].get('ready'),seconds=30)
  healthy(before)
  # Exclusive command file access reproduced a broken HTTP connection in V1.22.
  with FileHold('display_command.txt',0):
   rows=sample_for(2.2,{'COMMAND_UNAVAILABLE'})
   assert rows[-1]['state']['captures']>rows[0]['state']['captures']
   assert all(r['state']['stimulus_status']['requested']=='real_video' for r in rows)
   ui_checkpoint('command_lock')
  after=until(lambda s:s['stimulus_status']['ready']);healthy(after)
  assert after['stimulus_status']['rendered_frames']>before['stimulus_status']['rendered_frames']
  proof['command_lock']=dict(passed=True,before=before,rows=rows,after=after)
  dump('command_lock.json',proof['command_lock']);print('Actual exclusive command lock: HTTP stayed responsive, acquisition/rendering continued',flush=True)
  # Readers allowed, replacement denied: retain a REAL old report, not fake JSON.
  until(lambda s:s['stimulus_status']['ready'] and s['stimulus_status']['age_seconds']<.12)
  with FileHold('player_status.json',1):
   action('display',value='station_6')
   pending=state();healthy(pending)
   assert pending['stimulus_status']['state']=='SWITCHING'
   assert pending['stimulus_status']['requested']=='station_6' and pending['stimulus_status']['observed']=='real_video'
   rows=sample_for(2.2,{'SWITCHING','STALE'});stale=rows[-1]['state']
   assert stale['stimulus_status']['state']=='STALE' and not stale['stimulus_status']['ready']
   assert stale['captures']>pending['captures']
   ui_checkpoint('stale_player')
  after=until(lambda s:s['stimulus_status']['ready'] and s['stimulus_status']['observed']=='station_6');healthy(after)
  proof['telemetry_held']=dict(passed=True,pending=pending,rows=rows,after=after)
  dump('telemetry_held.json',proof['telemetry_held']);print('Actual report retained: SWITCHING then STALE, refresh confirms the new source',flush=True)
  with FileHold('player_status.json',0):rows=sample_for(1.0,{'PLAYER_UNAVAILABLE'})
  after=until(lambda s:s['stimulus_status']['ready']);healthy(after)
  proof['telemetry_unreadable']=dict(passed=True,rows=rows,after=after);dump('telemetry_unreadable.json',proof['telemetry_unreadable'])
  action('display',value='real_video');final=until(lambda s:s['stimulus_status']['ready'] and s['stimulus_status']['observed']=='real_video');healthy(final)
  for key in ('boot_id','invalid','gaps','dropped','ack_errors','descriptor_crc_errors'):assert final['board_stats'][key]==before['board_stats'][key],key
  assert final['records_total']==before['records_total'] and final['storage']['mode']=='preview'
  proof.update(passed=True,before=before,after=final,no_new_records=True)
  dump('summary.json',proof);print('Three actual file synchronization cases passed; no new errors or records',flush=True)
 except Exception as e:proof['error']=str(e);dump(f'failure_{time.time_ns()}.json',proof);raise
 finally:action('storage',mode='preview',max_archive_mib=1024);action('display',value='real_video');action('start')
if __name__=='__main__':run()
