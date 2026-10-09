from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
p=R/'sim/tb_capture_crc.sv';s=p.read_text().replace("32'h54465335","32'h54465336")
# Move the output stall into TRAILER after the new 40-cycle metadata scan.
s=s.replace('repeat(9)@(negedge clk);ready=0;repeat(7)', 'repeat(49)@(negedge clk);ready=0;repeat(7)')
p.write_text(s)
p=R/'sim/tb_capture_sg.sv';p.write_text(p.read_text().replace("32'h54465335","32'h54465336"))
p=R/'scripts/check_crc_sim.py';s=p.read_text().replace('0x54465335','0x54465336')
s=s.replace('bad=bool(m[6]&0x80000000);', "descriptor=list(m);descriptor[8]=0;descriptor_crc=zlib.crc32(struct.pack('<40I',*descriptor));assert descriptor_crc==m[8],('descriptor CRC',idx)\n bad=bool(m[6]&0x80000000);")
s=s.replace('pl_crc=m[1],received_crc=actual','pl_crc=m[1],received_crc=actual,descriptor_crc=m[8]')
s=s.replace('reset/trailer stalls', '7 descriptors against independent zlib, reset/trailer stalls')
p.write_text(s)
plan=json.loads((R/'ITERATION_PLAN.json').read_text());plan['hardware']='V1.14 PL descriptor CRC, build pending';(R/'ITERATION_PLAN.json').write_text(json.dumps(plan,indent=2))
(R/'README.md').write_text('# PYNQ-Z2 Tile V1.14\n\nPL 描述 CRC 版本，构建和验收进行中。V1.13 工程与 ZIP 保留。\n',encoding='utf-8')
(R/'host/benchmark.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><h1>V1.14 描述校验 · 验收进行中</h1><p>新 FPGA 硬件尚在构建。旧 V1.13 完整保留。</p><a href="/">返回工作站</a></html>',encoding='utf-8')
print('V1.14 CRC simulation updated; new hardware not yet accepted')
