from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=R/'host/workstation.html';s=p.read_text(encoding='utf-8-sig')
assert 'id="resumePending"' not in s
s=s.replace('<button class="wide danger" id="stop">停止接收</button>','<button class="wide danger" id="stop">停止接收</button><button class="wide" id="resumePending" hidden>恢复待确认</button>')
s=s.replace('<div class="warning error" id="error" role="alert"></div>','<div class="warning error" id="error" role="alert"></div><div class="warning" id="syncWarning" role="status" hidden></div>')
s=s.replace("const recovering=!!s.recovery?.active;", """const recovering=!!s.recovery?.active;
$('resumePending').hidden=!s.pending_operation;
$('resumePending').disabled=s.busy||s.enabled||recovering||!!s.confirmation_journal?.error;
const syncText=s.synchronization_warning||(s.pending_confirmation?'已有事件等待确认：恢复会先核对板卡启动号和队列，保留已存截图，不直接抓取下一张。':'');
$('syncWarning').hidden=!syncText;$('syncWarning').textContent=syncText;""")
s=s.replace("$('start').disabled=s.enabled;", "$('start').disabled=s.enabled||!!s.confirmation_journal?.error;")
s=s.replace("$('capture').disabled=s.busy||recovering||!!s.pending_operation;", "$('capture').disabled=s.busy||recovering||!!s.pending_operation||!!s.confirmation_journal?.error;")
s=s.replace("$('start').onclick=()=>act('start');", "$('start').onclick=()=>act('start');$('resumePending').onclick=()=>act('resume_pending');")
p.write_text(s,encoding='utf-8')
(R/'host/benchmark.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Tile V1.13 验收进行中</title><body><a href="/">返回工作台</a><h1>V1.13 待确认恢复 · 验收进行中</h1><p>本版正在验证本地持久确认与启动号变化。尚未发布本版通过结论。旧 V1.12 已单独保存。</p></body></html>''',encoding='utf-8')
p=R/'host/workstation.py';s=p.read_text(encoding='utf-8');s=s.replace('reports/v132/header_validation_summary.json','reports/v132/journal_validation_summary.json');p.write_text(s,encoding='utf-8')
(R/'README.md').write_text('# PYNQ-Z2 Tile V1.13\n\n待确认恢复版本，验收进行中。旧 V1.12 工程与 ZIP 备份保留。\n',encoding='utf-8')
print('V1.13 pending-confirmation UI and honest pending benchmark prepared')
