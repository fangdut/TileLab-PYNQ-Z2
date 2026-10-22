from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=P/'reports/v182/hls64';out.mkdir(parents=True,exist_ok=False)
for a,b in [(W/'v182_all_c01/summary.json','full_c_summary.json'),(W/'v182_all_c01/results.json','full_c_results.json'),(W/'v170_hls64/solution/syn/report/texture_integer_csynth.xml','csynth.xml'),(W/'v170_hls64/solution/syn/report/decode_operation_csynth.xml','decode_csynth.xml'),(W/'v170_hls64/solution/syn/verilog/texture_integer_decode_operation.v','generated_decode.v'),(W/'v182_recurrence64.json','recurrence.json'),(W/'v182_decode_structure64.json','generated_structure.json')]:shutil.copy2(a,out/b)
c=json.loads((out/'full_c_summary.json').read_text());assert c['cases']==c['correct']==117 and c['all_grid_values_exact'] and c['all_original_size_masks_exact']
compared=[]
for p in sorted((W/'v182_all_c01').glob('*/result.bin')):
    old=W/'v179_all_c05'/p.parent.name/'result.bin';assert p.read_bytes()==old.read_bytes();compared.append(dict(id=p.parent.name,bytes=p.stat().st_size,result_sha256=sha(p)))
assert len(compared)==117;(out/'complete_output_manifest.json').write_text(json.dumps(compared,indent=2)+'\n')
x=ET.parse(out/'csynth.xml').getroot();j=dict(scope='C_AND_SYNTHESIS_ONLY_NOT_FULL_RTL_OR_BOARD',source_sha256=c['source_sha256'],all117_complete_output_files_identical=True,baseline='acceptedHLS62/v179_all_c05',estimated_clock_ns=float(x.findtext('./PerformanceEstimates/SummaryOfTimingAnalysis/EstimatedClockPeriod')),resources={p.tag:int(p.text) for p in x.find('./AreaEstimates/Resources')},board_programmed=False)
(out/'experiment.json').write_text(json.dumps(j,indent=2)+'\n')
for folder in ['decoder_checks01','decode_structure_negative01']:
    source=W/('v182_'+folder);target=P/'reports/v182'/folder;target.mkdir(parents=True,exist_ok=False)
    shutil.copy2(source/'summary.json',target/'summary.json')
    if (source/'test.log').exists():shutil.copy2(source/'test.log',target/'test.log')
repro=P/'reports/v182/reproduction';repro.mkdir(exist_ok=False)
for name in ['prepare_v182_decode01.py','start_v182_decode_full_c.py','start_v182_hls64_synth.py','start_v182_hls65_full.py','start_v182_physical01.py','test_v182_decoder01.py','test_v182_decode_structure01.py','checkpoint_v182_pending01.py']:
    shutil.copy2(W/name,repro/name)
repro=P/'reports/v180/reproduction';shutil.copy2(W/'archive_v180_rejection_and181.py',repro/'archive_v180_rejection_and181.py')
p=R/'README.md';s=p.read_text(encoding='utf8');old='整机实现进行中；Winograd 仅完成独立数学检查，尚未接入检测器';assert old in s;s=s.replace(old,'125 MHz 实际建立时间 −0.598 ns，未通过、未下载；Winograd 仅完成独立数学检查，尚未接入检测器')
where=s.index('\n117 张为反复使用');s=s[:where]+'\n| V182 指令控制译码（HLS64/65） | 117 张完整 C 输出与已验收版字节一致；100,268 个操作码检查及四种非法模型错误路径一致；生成 RTL 已确认两级译码寄存 | 完整 RTL 仿真进行中，尚无新的整机时序与实板结果 |\n'+s[where:];p.write_text(s,encoding='utf8')
p=R/'FPGA_MIGRATION_STATUS.md';s=p.read_text(encoding='utf8');a='Full implementation is running; no125MHz or newFPS result.';assert a in s;s=s.replace(a,'Actual125MHz implementation fails setup-0.598ns,hold+0.037ns,DRC0,DSP218; never programmed. The large-deficit retry gate stops repeated physical repair. No125MHz or newFPS result.')
where=s.index('\n\n## Archived development history');s=s[:where]+'''\n\nCurrent V182 targets the measured V180 control path: rawopcode bit27 (t_1_load_reg_11896) toBRAMwriteenable,7.641nsdata83.14%route. A separate two-stage,three-bit onehot decoder recognizes raw32 opcodes1/2/3; conv receives decoded depth explicitly, and unsupported opcodes retain error3. It derives the V181 residualstream proposal, which itself passes C117 and synthesis but has noRTL/board result. HLS64/sourcec4391bbdd3da915836e2f6f63c97407bfd120456f3274d95a1fcf71e6ec4abbd passes all117complete output file comparisons,100268scalar opcodes and4invalid-model error paths. HLSestimates214DSP251BRAM18,71919LUT69861FF,8.207ns. Generated decoder latency2/II1/3bits is checked; mutated width/stage/latency fixtures reject. Source-identical HLS65 fullRTL/IP is running, after which one guarded split125MHz physical trial may run. Resolution/model/threshold are unchanged. Accepted firmware remains V1798.17FPS.''' +s[where:];p.write_text(s,encoding='utf8')
print(json.dumps(j))
