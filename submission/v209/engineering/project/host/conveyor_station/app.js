const display=location.pathname==='/display';
if(display)document.body.classList.add('display');
if(new URLSearchParams(location.search).get('replay')==='automation'){
 const banner=document.createElement('div');banner.textContent='联调自动回放 · 操作由程序执行（非人工）';
 banner.style.cssText='position:fixed;top:0;left:0;right:0;text-align:center;background:#73551f;color:#fff1c5;font-size:12px;z-index:20;padding:3px';document.body.append(banner);
}
const $=id=>document.getElementById(id);
let S=null,receivedAt=0,photoKey='',photoReady=false,overlayKey='',pendingCapture='',captureBusy=false,showOverlay=true,queueBuilt=false,lastResult='',busy=false,lastPoll=0,loadGeneration=0;
const labels={IDLE:'等待入线',MOVING:'瓷砖匀速进入检测区',CAPTURE:'移动中截帧 · 输送继续',SUBMITTING:'移动帧正在送往 FPGA · 输送继续',INSPECTING:'FPGA 正在检测 · 瓷砖继续前进',AUTO_CONFIRM:'FPGA 未报警 · 正在校验自动通过',PASSING:'FPGA 未报警 · 匀速自动通过',DEFECT_APPROACH:'FPGA 发现疑似缺陷 · 前往复核区',REVIEW:'异常瓷砖已停在复核区 · 等待人工复核',CONFIRMING:'复核已记录 · 正在校验处置',OUTGOING:'复核完成 · 瓷砖离开复核区',FAULT:'流水线停止 · 请检查'};
async function request(path,body,headers){
 const r=await fetch(path,body===undefined?{cache:'no-store'}:{method:'POST',body:headers?body:JSON.stringify(body),headers:headers||{'Content-Type':'application/json'}});
 const data=await r.json();if(!r.ok)throw Error(data.error||r.statusText);return data;
}
async function act(op,extra={}){if(busy||!S)return;busy=true;try{apply(await request('/api/action',{run:S.run,op,...extra}));$('error').textContent=''}catch(e){$('error').textContent=e.message}finally{busy=false}}
function apply(state){
 S=state;receivedAt=performance.now();lastPoll=receivedAt;
 const c=S.cycle,r=c?.result;let key=S.row?'/photo/'+S.row.id:c?'/image?cycle='+c.id+'&kind=input':'';
 if(key!==photoKey){photoKey=key;photoReady=false;overlayKey='';$('overlay').style.display='none';const generation=++loadGeneration;if(key){const img=new Image();img.onload=()=>{if(generation!==loadGeneration)return;const canvas=$('frame');canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;canvas.getContext('2d').drawImage(img,0,0);photoReady=true};img.onerror=()=>{$('error').textContent='入线照片载入失败，流水线保持等待'};img.src=key}}
 const validResult=r&&!['IDLE','MOVING','CAPTURE','FAULT'].includes(S.phase);
 if(validResult){const k='/image?cycle='+c.id+'&kind=overlay';if(k!==overlayKey){overlayKey=k;$('overlay').src=k}$('overlay').style.display=showOverlay?'block':'none'}else{$('overlay').style.display='none'}
 $('tile').className='tile'+(validResult?(r.pl_image_alarm?' alarm':' good'):'');
 $('tileTag').textContent=validResult?(r.pl_image_alarm?'FPGA：疑似缺陷':'FPGA：未报警'):'真实瓷砖照片 · 尚未返回判定';
 $('tileTag').style.color=validResult?(r.pl_image_alarm?'var(--red)':'var(--mint)'):'var(--dim)';
 $('status').textContent=S.motion?.waiting_for_result?'结果尚未就绪 · 已在复核区停下等待':labels[S.phase]||S.phase;
 $('status').style.color=S.phase==='FAULT'?'var(--red)':validResult&&r.pl_image_alarm?'var(--red)':'var(--ink)';
 $('sampleName').textContent=S.row?.name||c?.name||'等待工件';
 $('connection').textContent='● '+(S.connection?'FPGA 已连接':'等待 FPGA');
 let detail=S.error|| (validResult?`工件 ${c.id.slice(0,8)} · FPGA 帧号 ${r.pl_frame_sequence} · ${c.review?'人工复核已记录':r.pl_image_alarm?'到右侧复核区后保持停驻':'按未报警策略自动通过，无需逐张复核'}`:S.row?`${S.row.name} · 检测区预留 ${S.zone_seconds} 秒 · 进入即截帧，继续匀速前进`:'选择真实照片队列后启动');
 $('detail').textContent=detail;
 $('metrics').innerHTML=validResult?`${(r.pl_engine_seconds*1000).toFixed(1)} ms / ${(r.wall_seconds*1000).toFixed(1)} ms<small>FPGA 计算 / 传图与检测</small>`:'—<small>等待本块 FPGA 结果</small>';
 const step=S.phase==='MOVING'?'enter':['CAPTURE','SUBMITTING','INSPECTING'].includes(S.phase)?'inspect':['DEFECT_APPROACH','REVIEW','CONFIRMING'].includes(S.phase)?'review':['PASSING','AUTO_CONFIRM','OUTGOING'].includes(S.phase)?'leave':'';
 document.querySelectorAll('[data-step]').forEach(el=>el.classList.toggle('active',el.dataset.step===step));
 if(!queueBuilt&&S.samples.length){const defaultIds=S.samples.slice(0,new URLSearchParams(location.search).has('filming')?3:4).map(s=>s.id);$('samples').replaceChildren(...S.samples.map(sample=>{const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=sample.id;input.checked=defaultIds.includes(sample.id);label.append(input,document.createTextNode(sample.name));return label}));queueBuilt=true}
 $('start').disabled=!['IDLE','REVIEW'].includes(S.phase)||S.enabled||!S.calibrated;
 $('start').textContent=!S.calibrated?'请先完成工位核验':S.enabled?'队列运行中':S.phase==='REVIEW'?'复核后启动队列':'启动队列';
 $('pause').disabled=!S.enabled;
 const canReview=S.phase==='REVIEW'&&!!r;['good','defect','uncertain'].forEach(id=>$(id).disabled=!canReview);
 if(r?.id!==lastResult){lastResult=r?.id||'';$('note').value=''}
 if(S.review_ack)$('seen').checked=true;
 $('history').replaceChildren(...S.history.slice().reverse().map(h=>{const div=document.createElement('div');div.className='record';div.textContent=h.automatic?`${h.cycle_id.slice(0,8)} · FPGA 未报警 · 自动通过（未经人工复核）`:`${h.cycle_id.slice(0,8)} · FPGA ${h.alarm?'报警':'未报警'} · 复核${{good:'正常',defect:'缺陷',uncertain:'待定'}[h.review?.verdict]} · ${{release:'放行',segregate:'隔离',remove_unvalidated:'移出'}[h.disposition.command]||h.disposition.command}`;const small=document.createElement('small');small.textContent='　'+(h.review?.operator||'系统自动策略');div.append(small);return div}));
 if(S.error)$('error').textContent=S.error;
 // Capture must not depend on requestAnimationFrame: a second operator window
 // can make the display tab a background page while inference still progresses.
 if(S.phase==='CAPTURE')capture();
}
async function capture(){
 if(!display||captureBusy||!S||S.phase!=='CAPTURE'||!photoReady||pendingCapture===S.token)return;
 const token=S.token;captureBusy=true;pendingCapture=token;
 try{const blob=await new Promise(resolve=>$('frame').toBlob(resolve,'image/png'));if(!blob)throw Error('浏览器截帧失败');await request('/api/capture',blob,{'Content-Type':'image/png','X-Capture-Token':token})}catch(e){$('error').textContent=e.message;pendingCapture=''}finally{captureBusy=false}
}
function animate(){
 if(S){const dt=(performance.now()-receivedAt)/1000;let x=S.motion?.x??780;
 if(S.motion?.moving)x=Math.min(S.motion.maximum,x+S.motion.velocity*dt);
 $('tile').style.left=x+'px';$('tile').hidden=!photoReady||S.phase==='IDLE'||(S.phase==='FAULT'&&!S.cycle);$('empty').hidden=!$('tile').hidden;
 $('belt').style.backgroundPositionX=x+'px';
 if(S.phase==='CAPTURE')capture();
 if(lastPoll&&performance.now()-lastPoll>3000){$('status').textContent='连接中断 · 画面冻结';$('overlay').style.display='none'}
 }
 requestAnimationFrame(animate);
}
async function poll(){try{apply(await request('/api/state'))}catch(e){$('error').textContent='连接中断：'+e.message}setTimeout(poll,200)}
$('start').onclick=()=>act('start',{queue:[...document.querySelectorAll('#samples input:checked')].map(i=>i.value),zone_seconds:Number($('speed').value)});
$('pause').onclick=()=>act('pause');
for(const [id,verdict] of [['good','good'],['defect','defect'],['uncertain','uncertain']])$(id).onclick=()=>act('review',{result_id:S.cycle?.result?.id,operator:$('operator').value,verdict,note:$('note').value,confirmed:$('seen').checked});
$('toggle').onclick=()=>{showOverlay=!showOverlay;if(S)apply(S)};
$('seen').onchange=()=>{if($('seen').checked)act('ack_review',{confirmed:true});else if(S?.review_ack)$('seen').checked=true};
$('operator').value=sessionStorage.getItem('tilelab.operator')||'';
$('operator').oninput=()=>sessionStorage.setItem('tilelab.operator',$('operator').value);
new ResizeObserver(entries=>{const box=entries[0].contentRect;document.documentElement.style.setProperty('--scale',Math.min(box.width/1280,box.height/540))}).observe($('viewport'));
poll();animate();
