from pathlib import Path
p=Path(__file__).resolve().parents[1]/'host/workstation.html'
s=p.read_text(encoding='utf-8').replace('Tile V1.3','Tile V1.4').replace('最多 500 条','完整留存 · 分页浏览 · 磁盘余量保护')
s=s.replace("cardSignature='',toastTimer;","cardSignature='',toastTimer,pageOffset=0,searchTimer,refreshBusy=false;")
s=s.replace('<div class="cards" id="cards">','<div class="panel-head"><span class="tiny" id="pageInfo">读取存档</span><div><button id="pagePrev">上一页</button> <button id="pageNext">下一页</button></div></div><div class="cards" id="cards">')
a=s.index('async function refresh()');b=s.index('\nfunction render()',a)
s=s[:a]+'''async function refresh(){if(refreshBusy)return;refreshBusy=true;try{const q=new URLSearchParams({offset:String(pageOffset),limit:'24',review:$('filter').value,query:$('search').value});const r=await fetch('/api/state?'+q);if(!r.ok)throw Error('状态读取失败');state=await r.json();render()}catch(e){$('connection').className='chip bad';$('connection').textContent='本地服务未连接'}finally{refreshBusy=false}}
'''+s[b:]
s=s.replace("rs.filter(x=>x.review==='pending'||x.review==='needs_recheck').length","s.archive?.pending??0").replace("rs.filter(x=>x.review==='confirmed_crack').length","s.archive?.confirmed??0").replace("rs.filter(x=>x.review==='false_alarm').length","s.archive?.false_alarm??0")
a=s.index('function renderCards(){');b=s.index('const sig=',a)
s=s[:a]+'''function renderCards(){const rows=state?.records||[];$('pageInfo').textContent=`共 ${state.records_total} 条 · 第 ${Math.floor(pageOffset/24)+1} / ${Math.max(1,Math.ceil(state.records_total/24))} 页`;$('pagePrev').disabled=pageOffset===0;$('pageNext').disabled=pageOffset+24>=state.records_total;'''+s[b:]
s=s.replace("im.className='thumb';","im.className='thumb';im.loading='lazy';")
s=s.replace("$('filter').onchange=renderCards;$('search').oninput=renderCards;","$('filter').onchange=()=>{pageOffset=0;refresh()};$('search').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{pageOffset=0;refresh()},250)};$('pagePrev').onclick=()=>{pageOffset=Math.max(0,pageOffset-24);refresh()};$('pageNext').onclick=()=>{pageOffset+=24;refresh()};")
p.write_text(s,encoding='utf-8')
