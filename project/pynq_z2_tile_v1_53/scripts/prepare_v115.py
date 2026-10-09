from pathlib import Path
import json,hashlib,re
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_14';O=R/'reports/v132'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((B/'DELIVERY_MANIFEST.json').read_text(encoding='utf-8'))
assert sha(B/'rtl/frame_capture_sg.v')==old['source_sha256']['rtl/frame_capture_sg.v']
assert sha(R/'rtl/product_tracker.v')==sha(B/'rtl/product_tracker.v')
gold=(B/'rtl/frame_capture_sg.v').read_text().replace('module frame_capture #','module frame_capture_v114 #')
(R/'sim/frame_capture_v114_reference.v').write_text(gold,encoding='utf-8')
tb=(B/'sim/tb_capture_crc.sv').read_text();tb=tb.replace('module tb_capture_crc;','module tb_capture_equivalence;')
ports=['cap_seq','cap_count','cap_min','cap_max','cap_status','cap_config']
match=re.search(r' frame_capture #.*?\.cap_config\(\)\);',tb,re.S);assert match
original=match.group();actual=original;reference=original.replace('frame_capture #','frame_capture_v114 #').replace(' dut(', ' reference(')
for i,p in enumerate(ports):
 actual=actual.replace(f'.{p}()',f'.{p}(actual_cap[{32*i}+:32])')
 reference=reference.replace(f'.{p}()',f'.{p}(reference_cap[{32*i}+:32])')
reference=reference.replace('.m_axis_tdata(data)','.m_axis_tdata(reference_data)').replace('.m_axis_tvalid(valid)','.m_axis_tvalid(reference_valid)').replace('.m_axis_tlast(last)','.m_axis_tlast(reference_last)')
checking='''
 wire [191:0] actual_cap,reference_cap;
 wire [31:0] reference_data;wire reference_valid,reference_last;
 integer equivalent_cycles=0;
 always @(posedge clk)begin
  #1;
  if(!reset)begin
   equivalent_cycles=equivalent_cycles+1;
   if(valid!==reference_valid || last!==reference_last || (valid && data!==reference_data) || actual_cap!==reference_cap)
    $fatal(1,"V1.15/V1.14 observable cycle mismatch at cycle %0d",equivalent_cycles);
  end
 end
'''
tb=tb[:match.start()]+checking+actual+'\n'+reference+tb[match.end():]
tb=tb.replace('$fclose(output_file);$display(', '$display("EQUIVALENT_CYCLES=%0d",equivalent_cycles);$fclose(output_file);$display(')
(R/'sim/tb_capture_equivalence.sv').write_text(tb,encoding='utf-8')
tcl=(R/'scripts/test_capture_crc.tcl').read_text().replace('crc_test','equivalence_test').replace('reports/v132/crc_sim','reports/v132/equivalence_sim').replace('tb_capture_crc','tb_capture_equivalence')
tcl=tcl.replace('$root/rtl/product_tracker.v]','$root/rtl/product_tracker.v $root/sim/frame_capture_v114_reference.v]')
(R/'scripts/test_capture_equivalence.tcl').write_text(tcl,encoding='utf-8')
p=R/'host/workstation.py';s=p.read_text().replace("'1.15.0-iteration'","'1.15.0-shared-descriptor-port'").replace('descriptor_validation_summary.json','shared_port_validation_summary.json');p.write_text(s,encoding='utf-8')
plan=json.loads((R/'ITERATION_PLAN.json').read_text());plan.update(hardware='V1.15 shared descriptor read port, build and board validation pending',baseline_rtl_sha256=sha(B/'rtl/frame_capture_sg.v'));(R/'ITERATION_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.15 — 开发中

本版尝试复用描述 CRC 和 AXIS 输出的数组读取索引，以减少 LUT。尚未完成综合收益测量、全工程实现或上板验收。

当前可回退版本为 D:/Vivado/pynq_z2_tile_v1_14，原工程完整保留，另有 _baseline_backups/tile_v1_14_before_v1_15.zip。
工作区为 pynq_z2_tile_v1_53.sdk；硬件下载文件目前仍是继承种子，不能当作新硬件验收结果。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>TileLab V1.15 验收进行中</title><body style="font:18px/1.8 system-ui;padding:40px"><a href="/">返回工作站</a><h1>V1.15 验收进行中</h1><p>目标：复用描述读取端口，保留 V1.14 校验和检测行为，减少硬件资源。</p><p>尚未完成全工程实现与上板验收；当前稳定版本为 V1.14。</p></body></html>''',encoding='utf-8')
print('V1.15 prepared; equivalence reference is the manifest-verified V1.14 RTL')
