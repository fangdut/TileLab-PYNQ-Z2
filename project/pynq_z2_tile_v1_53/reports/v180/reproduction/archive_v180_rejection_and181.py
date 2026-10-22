from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET,struct
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads((W/'v180_physical_pipeline01.json').read_text());assert state['status']=='FAILED_NO_PROMOTION' and not state['board_programmed']
out=P/'reports/v180/hw01_125mhz_rejected';out.mkdir(parents=True,exist_ok=False)
for name in ['implementation_status.json','timing_summary.rpt','utilization.rpt','synthesis_utilization.rpt','clocks.rpt','drc.rpt','candidate_preflight.json','optimization_strategy.json']:
    source=W/'v180_hw01'/name
    if source.exists():shutil.copy2(source,out/name)
shutil.copy2(W/'v180_physical_pipeline01.json',out/'pipeline.json')
graph=json.loads((W/'v170_fullint224/graph.json').read_text());raw=(W/'v170_fullint224/model.bin').read_bytes();words=struct.unpack('<'+'I'*(len(raw)//4),raw);opcodes=[words[64+i*24] for i in range(words[2])];assert opcodes==[t[0] for t in graph['tasks']] and set(opcodes)=={1,2,3}
rtl=W/'v170_hls62/solution/syn/verilog/texture_integer.v';lines=[s for s in rtl.read_text().splitlines() if 't_1_load_reg_11896' in s];assert any('[31:0]' in s for s in lines) and any("== 32'd2" in s for s in lines)
(out/'opcode_rtl_evidence.txt').write_text('\n'.join(lines)+'\n')
proof=dict(scope='ROUTED_FAILURE_DIAGNOSIS_NOT_NEW_SPEED_OR_TIMING_PASS',clock_mhz=125,setup_slack_ns=-.598,hold_slack_ns=.037,drc_errors=0,board_programmed=False,source_register='t_1_load_reg_11896_reg[27]',destination='ram_U/ram_reg_0/WEA[0]',data_path_ns=7.641,route_fraction=.83143,timing_report_sha256=sha(W/'v180_hw01/timing_summary.rpt'),rtl_sha256=sha(rtl),model_sha256=hashlib.sha256(raw).hexdigest(),binary_descriptor_count=len(opcodes),opcodes=opcodes,interpretation='The raw32 opcode comparison now drives the worst BRAM write-enable path. Only opcodes1,2,3 are valid. Registeredonehot decoding is a new logic experiment; no new clock/FPS success is implied.')
(out/'critical_path_analysis.json').write_text(json.dumps(proof,indent=2)+'\n')
out=P/'reports/v181/hls63';out.mkdir(parents=True,exist_ok=False)
for a,b in [(W/'v181_all_c01/summary.json','full_c_summary.json'),(W/'v181_all_c01/results.json','full_c_results.json'),(W/'v170_hls63/solution/syn/report/texture_integer_csynth.xml','csynth.xml'),(W/'v181_offline_pipeline01.json','pipeline.json')]:shutil.copy2(a,out/b)
summary=json.loads((out/'full_c_summary.json').read_text());assert summary['cases']==summary['correct']==117
compared=[]
for p in sorted((W/'v181_all_c01').glob('*/result.bin')):
    old=W/'v179_all_c05'/p.parent.name/'result.bin';assert p.read_bytes()==old.read_bytes();compared.append(dict(id=p.parent.name,bytes=p.stat().st_size,result_sha256=sha(p)))
assert len(compared)==117
(out/'complete_output_manifest.json').write_text(json.dumps(compared,indent=2)+'\n')
xml=ET.parse(out/'csynth.xml').getroot();p=dict(scope='C_AND_HLS_SYNTHESIS_ONLY_NOT_RTL_OR_BOARD',source_sha256=summary['source_sha256'],all117_complete_output_files_identical=True,baseline='acceptedHLS62/v179_all_c05',estimated_clock_ns=float(xml.findtext('./PerformanceEstimates/SummaryOfTimingAnalysis/EstimatedClockPeriod')),resources={x.tag:int(x.text) for x in xml.find('./AreaEstimates/Resources')},board_programmed=False)
(out/'experiment.json').write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(dict(rejection=proof,offline181=p)))
