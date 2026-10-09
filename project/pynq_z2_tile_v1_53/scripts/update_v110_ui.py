from pathlib import Path
p=Path(__file__).resolve().parents[1]/'host/workstation.html';s=p.read_text(encoding='utf-8')
old='<button id="pause">暂停</button><button id="capture">手动留图</button>'
assert old in s
s=s.replace(old,'<button id="pause">冻结预览</button><button id="capture">板端抓拍</button><button class="wide danger" id="stop">停止接收</button>')
s=s.replace('预览优先显示历史待取事件，可能落后于显示器。','冻结预览时后台仍按存储设置接收事件，没有事件就不传整帧；只有“停止接收”才停止取图。停止后板端最多缓存 12 个事件，满后会丢失。板端抓拍读取待取事件或新抽样帧，不是保存冻结画面。预览优先显示历史待取事件，可能落后于显示器。')
s=s.replace("$('pause').onclick=()=>act('pause');","$('pause').onclick=()=>act('freeze_preview',{enabled:!state?.preview_frozen});$('stop').onclick=()=>act('pause');")
s=s.replace('if(s.frame){const f=s.frame;','if(s.frame&&(!s.preview_frozen||!liveFrame)){const f=s.frame;')
s=s.replace('if(key!==lastFrame)return;liveFrame=f;','if(key!==lastFrame||(state?.preview_frozen&&liveFrame))return;liveFrame=f;')
s=s.replace("const recovering=!!s.recovery?.active;","const recovering=!!s.recovery?.active;\n$('pause').textContent=s.preview_frozen?'恢复预览':'冻结预览';$('pause').disabled=!s.frame;$('stop').disabled=!s.enabled&&!s.busy&&!recovering;")
s=s.replace("(held?'保留画面 · 非当前实时 / ':'')+kind", "(state?.preview_frozen&&state?.enabled&&!state?.error?'预览已冻结 · 后台接收运行 / ':held?'保留画面 · 非当前实时 / ':'')+kind")
s=s.replace("s.enabled?'采集中'", "s.enabled?(s.preview_frozen?'后台接收事件':'采集中')")
s=s.replace('暂停只停止电脑接收。','冻结预览保持后台接收；停止接收会消耗有限的板端事件缓存。')
p.write_text(s,encoding='utf-8');print('Freeze view and stop receiver separated')
