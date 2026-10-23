from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET,re
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=json.loads((W/'v183_physical_pipeline01.json').read_text());assert j['status']=='FAILED_NO_PROMOTION' and not j['board_programmed']
out=P/'reports/v183/hw01_repair_rejected';out.mkdir(exist_ok=False)
for name in ['timing_summary.rpt','implementation_status.json','utilization.rpt','drc.rpt','clocks.rpt','bus_skew.rpt']:
 shutil.copy2(W/'v183_hw01/physical_repair01'/name,out/name)
shutil.copy2(W/'v183_physical_pipeline01.json',out/'pipeline.json')
failure=dict(scope='FAILED_PHYSICAL_TIMING_NOT_BOARD',initial_setup_ns=-.342,repair_setup_ns=-.015,hold_ns=.050,drc_errors=0,actual_dsp=219,board_programmed=False,
 repaired_path='top x counter bit0 to tmp28 bit0 replicate,7.172nsdata77.537%route',accepted_firmware_remains='V179/HLS62 100MHz8.16955FPS')
(out/'diagnosis.json').write_text(json.dumps(failure,indent=2)+'\n')
out=P/'reports/v185/hls68';out.mkdir(parents=True,exist_ok=False)
for a,b in [('v185_all_c01/summary.json','full_c_summary.json'),('v185_all_c01/results.json','full_c_results.json'),('v185_all_c01/complete_output_manifest.json','complete_output_manifest.json'),('v170_hls68/solution/syn/report/texture_integer_csynth.xml','csynth.xml'),('v185_generated_structure68.json','generated_structure.json'),('v185_recurrence68.json','recurrence.json'),('v185_quarter_unit_rtl01/summary.json','unit_rtl.json'),('v185_quarter_unit_rtl01/xsim.log','unit_xsim.log'),('v185_structure_negative01/summary.json','structure_negative.json')]:shutil.copy2(W/a,out/b)
for n in ['quarter_horizontal','quarter_vertical']:
 for a,b in [('report/'+n+'_csynth.xml',n+'_csynth.xml'),('verilog/texture_integer_'+n+'.v','generated_'+n+'.v')]:shutil.copy2(W/'v170_hls68/solution/syn'/a,out/b)
c=json.loads((out/'full_c_summary.json').read_text());assert c['cases']==c['correct']==117
assert len(json.loads((out/'complete_output_manifest.json').read_text()))==117
old=(P/'experimental/texture_v170/hls/frozen/v170_hls66.cpp').read_text();new=(P/'experimental/texture_v170/hls/frozen/v170_hls68.cpp').read_text()
rowpattern=r'static ap_uint<21> row_offset\(.*?\n\}'
assert re.search(rowpattern,old,re.S).group()==re.search(rowpattern,new,re.S).group()
guardpattern=r'    if\(h\[0\]!=0x17000001\|\|!width.*?return;'
assert re.search(guardpattern,old).group()==re.search(guardpattern,new).group()
from sys import path
path.insert(0,str(P/'tools/fpga_texture_v170'))
from check_row_address import inspect
row=inspect(W/'v170_hls68');assert row['source_sha256']==c['source_sha256'];(out/'row_generated_structure.json').write_text(json.dumps(row,indent=2)+'\n')
x=ET.parse(out/'csynth.xml').getroot();proof=dict(scope='C_SYNTHESIS_AND_QUARTER_UNIT_RTL_NOT_FULL_DETECTOR_RTL_OR_BOARD',source_sha256=c['source_sha256'],model_sha256=c['model_sha256'],all117_complete_output_files_identical=True,baseline='acceptedHLS62/v179_all_c05',resources={n.tag:int(n.text) for n in x.find('./AreaEstimates/Resources')},estimated_clock_ns=float(x.findtext('./PerformanceEstimates/SummaryOfTimingAnalysis/EstimatedClockPeriod')),horizontal_unit_cases=262144,vertical_unit_cases=131088,row_helper_and_size_guard_byte_identical_to_exhaustively_checked_hls66=True,board_programmed=False,full_detector_rtl_passed=False,full_hls69_state_at_archive=json.loads((W/'v185_hls69_full_pipeline.json').read_text())['status'])
(out/'experiment.json').write_text(json.dumps(proof,indent=2)+'\n')
repro=P/'reports/v185/reproduction';repro.mkdir()
for name in ['prepare_v185_quarter01.py','start_v185_quarter_full_c.py','start_v185_hls68_synth.py','start_v185_hls69_full.py','test_v185_structure_negative01.py','start_v185_physical01.py','collect_v185_verified.py','archive_v185_offline01.py']:shutil.copy2(W/name,repro/name)
p=R/'README.md';s=p.read_text(encoding='utf8');s=s.replace('一次物理修复进行中；暂无新实板吞吐','一次物理修复后仍为 −0.015 ns，未通过、未下载；暂无新实板吞吐')
s=s.replace('完整 C 回归与 HLS68 综合进行中，尚无新吞吐结果','117 张完整输出字节一致；39 万次生成 RTL 单元检查、结构检查与 HLS68 综合通过；HLS69 完整检测器 RTL 正在验证，尚无新实板吞吐')
p.write_text(s,encoding='utf8')
p=R/'FPGA_MIGRATION_STATUS.md';s=p.read_text(encoding='utf8');s=s.replace('one guarded physical repair still running.','one guarded repair ends atsetup-0.015ns,hold+0.050ns,DRC0,DSP219; never programmed.')
s=s.replace('C117/synth68 running; no new actualFPS claim.','C117complete outputs byte-identical179;generatedquarterunit262144horizontal/131088vertical cases pass;registeredstructure and6negative checks pass. HLS68estimate213DSP251BRAM18,70949LUT70171FF,8.207ns. Rowhelper/sizeguardbyteidentical66,generatedrowstructurepasses. Source-identical HLS69 fullRTL/IP is running after failed183; one guarded fresh125MHzsplit physical trial waits for fullRTL. No new actualFPS claim.')
p.write_text(s,encoding='utf8');print(json.dumps(dict(failure=failure,offline185=proof)))
