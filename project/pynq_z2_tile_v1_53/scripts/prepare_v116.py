from pathlib import Path
import re,json
R=Path(__file__).resolve().parents[1]
p=R/'host/workstation.py';s=p.read_text();s=re.sub(r"workstation_release='[^']+'","workstation_release='1.16.0-irq-context'",s);s=s.replace('shared_port_validation_summary.json','irq_context_validation_summary.json');p.write_text(s,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.16（开发与验收中）

本版目标：通过可复现 BSP 配置保护 Cortex-A9 中断浮点上下文，保留整数 memcpy，增加 IRQ 栈余量，并用实际 GIC 中断做新旧对照。

FPGA 使用已验收 V1.15 的同一 BIT/XSA/LTX，视觉算法和硬件时钟不变。V1.15 原工程完整保留，另有源码及下载文件 ZIP：D:/Vivado/_baseline_backups/tile_v1_15_before_v1_16.zip。

目前不能把目录存在或 BSP 编译完成当作实板通过。完成以 DELIVERY_MANIFEST.json 和本版实测报告为准。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>V1.16 验证进行中</title><body style="font:18px/1.8 system-ui;padding:40px"><a href="/">返回工作站</a><h1>V1.16 中断上下文验证进行中</h1><p>尚未完成实板新旧对照及完整回归。当前已验收基线为 V1.15。</p></body></html>''',encoding='utf-8')
print('V1.16 pending state prepared; V1.15 remains the validated baseline')
