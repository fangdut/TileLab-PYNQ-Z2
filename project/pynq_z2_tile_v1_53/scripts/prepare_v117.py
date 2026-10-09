from pathlib import Path
import re
R=Path(__file__).resolve().parents[1]
p=R/'host/workstation.py';s=p.read_text();s=re.sub(r"workstation_release='[^']+'","workstation_release='1.17.0-event-wrap'",s);s=s.replace('irq_context_validation_summary.json','queue_wrap_validation_summary.json');p.write_text(s,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.17（开发与验收中）

本版目标：分离事件序号与物理环索引，支持 32 位事件编号回绕与事件 0 的确认，并同步修正 JTAG 调试读取逻辑。

V1.16 原工程完整保留并已备份。PL 保持已验收 V1.15 下载文件，Vitis 保留 V1.16 中断上下文保护和 4 KiB IRQ 栈。

尚未完成本版验收，以 DELIVERY_MANIFEST.json 和实测报告为准。
''',encoding='utf-8')
(R/'host/benchmark.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>V1.17 验证进行中</title><body style="font:18px/1.8 system-ui;padding:40px"><a href="/">返回工作站</a><h1>V1.17 事件编号回绕验证进行中</h1><p>当前已验收基线为 V1.16。本版尚未完成实板验收。</p></body></html>''',encoding='utf-8')
print('V1.17 pending; V1.16 preserved as accepted baseline')
