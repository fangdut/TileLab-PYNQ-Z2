from pathlib import Path
import hashlib,json,shutil
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=json.loads((W/'v182_physical_pipeline01.json').read_text());assert j['status']=='FAILED_NO_PROMOTION' and not j['board_programmed']
root=P/'reports/v182/hw01_125mhz_rejected';root.mkdir(parents=True,exist_ok=False)
names=['implementation_status.json','timing_summary.rpt','utilization.rpt','synthesis_utilization.rpt','clocks.rpt','drc.rpt','candidate_preflight.json','optimization_strategy.json']
for folder,target in [(W/'v182_hw01',root/'initial'),(W/'v182_hw01/physical_repair01',root/'single_repair')]:
 target.mkdir()
 for name in names:
  if (folder/name).exists():shutil.copy2(folder/name,target/name)
shutil.copy2(W/'v182_physical_pipeline01.json',root/'pipeline.json')
proof=dict(scope='FAILED_PHYSICAL_TIMING_NOT_BOARD',initial_setup_ns=-.490,repair_setup_ns=-.187,
 initial_hold_ns=.050,repair_hold_ns=.038,drc_errors=0,actual_dsp=219,board_programmed=False,
 initial_path='result header[4][4] to mask_pixels CE; 12 logic levels, 8.145ns data',
 repaired_path='HLS FSM[43] to row-address mul22x32 DSP cascade PCIN; 6.400ns data',
 accepted_firmware_remains='V179/HLS62 100MHz measured 8.169552657504967 HDMI FPS',
 reports={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()})
(root/'diagnosis.json').write_text(json.dumps(proof,indent=2)+'\n')
out=P/'reports/v183/rtl';out.mkdir(parents=True,exist_ok=False)
for source,name in [(W/'v183_latch_rtl01','result_latch'),(W/'v183_pipeline_rtl01','pipeline')]:
 dest=out/name;dest.mkdir()
 for f in ['summary.json','xsim.log']:shutil.copy2(source/f,dest/f)
shutil.copy2(W/'v183_rtl_gate01.json',out/'gate.json')
repro=P/'reports/v183/reproduction';repro.mkdir()
for name in ['start_v183_physical01.py','archive_v182_rejection_start183.py']:shutil.copy2(W/name,repro/name)
p=R/'README.md';s=p.read_text(encoding='utf8');s=s.replace('125 MHz 整机实现进行中，尚无新实板结果','125 MHz 建立时间初始 −0.490 ns、一次修复后 −0.187 ns，未通过、未下载')
where=s.index('\n117 张为反复使用');s=s[:where]+'\n| V183 结果校验流水线 | 与已验收历史 RTL 对照 6,190 次事务，覆盖错误头、DDR 错误、序号回绕及复位；采集/推理集成仿真通过，七组源文件绑定 | 沿用 HLS65，125 MHz 整机实现进行中；暂无新实板吞吐 |\n'+s[where:];p.write_text(s,encoding='utf8')
p=R/'FPGA_MIGRATION_STATUS.md';s=p.read_text(encoding='utf8');s=s.replace('One guarded split125MHz full physical trial is running; no new board result.','The split125MHz trial fails setup-0.490ns, then-0.187ns after one guarded repair; actualDSP219,DRC0. Never programmed. No new board result.')
where=s.index('\n\n## Archived development history');s=s[:where]+'''\n\nV183 pipelines the measured result-latch validation chain into separate expected-sequence, primitive-comparison and commit stages. It adds two control cycles without changing validation rules or CNN/model/threshold. Historical accepted RTL comparison passes6190transactions, including malformed headers, DDRerrors, sequencewrap, stickyfaults and reset; the complete capture/control integration fixture also passes. Seven source-bound RTL groups bind all11HDLs. Same HLS65/C117 and split125MHz physical trial running; no new actual FPS or timing pass.''' +s[where:];p.write_text(s,encoding='utf8')
print(json.dumps(proof))
