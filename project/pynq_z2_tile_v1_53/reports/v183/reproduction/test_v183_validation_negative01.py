from pathlib import Path
import subprocess,json,hashlib
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
base=P/'experimental/video_overlap_v175';out=W/'v183_validation_negative01';out.mkdir(exist_ok=False);code=(base/'rtl/pl_result_latch.sv').read_text()
mutations=[('skip_sequence','sequence_bad<=valid&&header[9]!=expected_sequence;','sequence_bad<=0;'),
 ('ignore_ddr_error','m_axi_rresp!=0||m_axi_rlast!=(index==9)','m_axi_rlast!=(index==9)'),
 ('alarm_on_equality','score_alarm<=header[3]>header[4];','score_alarm<=header[3]>=header[4];')]
results=[]
for name,a,b in mutations:
 assert code.count(a)==1
 root=out/name;(root/'rtl').mkdir(parents=True);(root/'sim').mkdir()
 (root/'rtl/pl_result_latch.sv').write_text(code.replace(a,b))
 for rel in ['test_result_latch.py','sim/pl_result_latch_reference_v176.sv','sim/tb_result_latch.sv']:(root/rel).write_bytes((base/rel).read_bytes())
 with (root/'driver.log').open('w') as log:
  r=subprocess.run(['D:/Vivado/TileLab_Runtime_V168/Scripts/python.exe','-X','utf8',str(root/'test_result_latch.py'),'--out',str(root/'run')],stdout=log,stderr=subprocess.STDOUT,timeout=120)
 log=(root/'run/xsim.log').read_text(errors='replace')
 assert r.returncode!=0 and 'Fatal:' in log and 'Result mismatch' in log,name
 results.append(dict(mutation=name,rejected=True,diagnostic=[s for s in log.splitlines() if 'Fatal:' in s]))
j=dict(scope='DELIBERATELY_BROKEN_RESULT_VALIDATION_REJECTS_NOT_BOARD',passed=True,source_sha256=hashlib.sha256((base/'rtl/pl_result_latch.sv').read_bytes()).hexdigest(),checks=results)
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
