"""Real event zero: saved evidence survives abrupt host exit and board reload."""
from pathlib import Path
import time,json
import board_v118_restart as restart
from board_v118_wrap import R,prepare_station,seed,restore

def run():
 out=R/'reports/v132/zero_restart'/str(time.time_ns());out.mkdir(parents=True)
 prepare_station(out);restart.OUT=out;results=[];seeds=[]
 try:
  for name,mode,reprogram in [('zero_before_ack','before_ack',False),('zero_after_ack','after_ack',False),('zero_new_boot','before_ack',True)]:
   proofdir=out/(name+'_seed');proofdir.mkdir();seeds.append(seed(0xffffffff,proofdir))
   result=restart.case(name,mode,reprogram)
   assert result['pending']['frame']['event_id']==0
   assert result['before']['head']==0xffffffff
   assert result['pending']['frame']['boot_id']==seeds[-1]['boot_id']
   assert result['saved_records']==1 and result['host_captures_after_restart']==0
   results.append(result)
 finally:
  clean=restore(out)
 summary=dict(passed=True,cases=results,seeds=seeds,clean_restart=clean,run_directory=str(out),scope='Actual release ELF and real HDMI frame; empty queue counters seeded before DMA; abrupt process termination and actual JTAG reload, not physical power-cycle')
 (out.parent/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(dict(passed=True,cases=len(results),clean_boot=clean['boot_id'])),flush=True)

if __name__=='__main__':run()
