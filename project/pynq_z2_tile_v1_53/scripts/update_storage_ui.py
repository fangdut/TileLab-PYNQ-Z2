from pathlib import Path
p=Path(__file__).resolve().parents[1]/'host/workstation.html'
s=p.read_text(encoding='utf-8')
anchor='<div class="control-label"><label for="recipe">'
block='''<div class="control-label"><label for="storageMode">证据存储</label></div><select id="storageMode" aria-label="证据存储"><option value="preview">仅预览 · 不自动存图</option><option value="archive">自动留图 · 满额转仅预览</option></select><div class="control-label"><label for="storageLimit">存档上限（MiB）</label></div><div class="threshold"><input id="storageLimit" type="number" min="16" max="102400" value="1024" aria-label="存档容量上限"><button id="applyStorage">应用存储设置</button></div><p class="footnote" id="storageUsage"></p><p class="footnote" id="storageNotice">仅预览会接收并确认板端事件，但不自动保存；红框和检测继续。手动留图仍占用存档容量。满额不删除旧记录。</p>'''
assert anchor in s and 'id="storageMode"' not in s
s=s.replace(anchor,block+anchor,1)
s=s.replace("function render(){const s=state,rs=s.records||[];","""function render(){const s=state,rs=s.records||[];
const st=s.storage||{};if(document.activeElement!==$('storageMode'))$('storageMode').value=st.mode||'preview';if(document.activeElement!==$('storageLimit'))$('storageLimit').value=st.max_archive_mib||1024;
$('storageUsage').textContent=`存档 ${((st.used_bytes||0)/1048576).toFixed(1)} / ${st.max_archive_mib||1024} MiB · 本次未存自动事件 ${st.not_archived_events||0} · 磁盘空闲 ${((st.free_disk_bytes||0)/1073741824).toFixed(1)} GiB`;
$('storageNotice').textContent=st.warning||((st.mode==='preview'?'仅预览：自动事件不保存，红框和检测继续；手动留图受容量上限约束。':'自动留图：保存后才确认；容量达到上限会转为仅预览并显示未存事件数。')+(st.at_limit?' 当前已有存档超出上限，旧数据不会自动删除。':''));
$('storageNotice').style.color=st.warning||st.at_limit?'#b43e39':'';
""")
s=s.replace("$('threshold').oninput", """$('applyStorage').onclick=async()=>{try{await post('/api/action',{op:'storage',mode:$('storageMode').value,max_archive_mib:Number($('storageLimit').value)});toast('存储设置已生效');await refresh()}catch(e){toast(e.message)}};
$('threshold').oninput""",1)
s=s.replace('全部保留</small>','存储模式与容量见采集控制</small>')
p.write_text(s,encoding='utf-8')
print('Storage controls added')
