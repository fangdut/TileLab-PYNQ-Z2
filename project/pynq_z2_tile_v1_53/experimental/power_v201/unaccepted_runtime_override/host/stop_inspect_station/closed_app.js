const $=id=>document.getElementById(id);
let state=null,pending=false,view='overlay',lastCycle=null,lastResult=null,lastRun=null,lastCertificate=null,lastMaterial=null,lastAuditRevision=-1;
const idle=['READY','RELEASED','SEGREGATED','REMOVED'];
const holds=['CALIBRATION_HOLD','REVIEW_HOLD','GOOD_HOLD','DEFECT_HOLD','CONFLICT_HOLD'];
const phaseNames={READY:'准备就绪',CONFIGURING:'正在核对参照与标定',STOPPED:'输入已固定',INSPECTING:'FPGA 检测中',CALIBRATION_HOLD:'核验结果 · 等待人工复核',REVIEW_HOLD:'检测结果 · 等待人工复核',GOOD_HOLD:'复核正常 · 等待确认放行',DEFECT_HOLD:'复核缺陷 · 等待隔离',CONFLICT_HOLD:'判断冲突 · 禁止良品放行',CONFIRMING:'正在核对并记录处置',RELEASED:'良品放行已确认',SEGREGATED:'缺陷隔离已确认',REMOVED:'本次样本处理完成',FAULT:'故障 · 禁止放行'};
const purposeNames={inspection:'正式检测',calibration_good:'良品核验',calibration_defect:'已知缺陷核验'};
const verdictNames={good:'正常',defect:'缺陷',uncertain:'待定'};
const dispositionNames={release:'确认放行',segregate:'确认隔离',remove_unvalidated:'待定／冲突移出',calibration_complete:'核验样本完成'};
const eventNames={material_created:'已建立材质记录',material_switch_started:'切换参照，旧结果作废',material_selected:'材质与板端参照已绑定',calibration_frozen:'本批标定核验已封存',input_frozen:'原图已固定',cycle_context_bound:'已绑定本次材质与标定批次',inspection_started:'已启动FPGA检测',inspection_completed:'已收到本次检测结果',manual_review_recorded:'已记录人工复核',disposition_requested:'正在核对处置条件',logical_disposition_confirmed:'已记录逻辑处置',fault:'故障，禁止放行',fault_reset:'故障已复位，旧结果作废',image_imported:'原图已导入'};
function txt(id,value){$(id).textContent=value}
function error(value){$('error').style.display=value?'block':'none';txt('error',value||'')}
function img(id,url){const target=$(id);if(!url){target.hidden=true;target.removeAttribute('src')}else{if(target.getAttribute('src')!==url)target.src=url;target.hidden=false}}
function options(id,rows,placeholder){
  const element=$(id),selected=element.value,signature=JSON.stringify(rows);
  if(element.dataset.options===signature)return;
  element.dataset.options=signature;element.replaceChildren();
  if(placeholder){const option=document.createElement('option');option.value='';option.textContent=placeholder;element.append(option)}
  for(const row of rows){const option=document.createElement('option');option.value=row.id;option.textContent=row.name;element.append(option)}
  if([...element.options].some(o=>o.value===selected))element.value=selected;
}
function render(s){
  state=s;const loop=s.closed_loop,cycle=s.cycle,result=cycle&&cycle.result,review=cycle&&cycle.review,phase=s.phase;
  const busy=pending||['CONFIGURING','INSPECTING','CONFIRMING'].includes(phase),isIdle=idle.includes(phase),actor=$('operator').value.trim();
  if(!loop){error('请使用已部署的标定与复核闭环工程。');return}
  const material=loop.active_material,run=loop.run,calibrated=loop.calibrated;
  txt('phase',phaseNames[phase]||phase);$('phase').className='state-'+phase;
  txt('item',cycle?cycle.name:'尚未载入本次样本');txt('connection',phase==='FAULT'?'连接或证据无效 · 待处理':'物理 FPGA · 已绑定本次启动');
  $('connection').className='badge '+(phase==='FAULT'?'':'live');
  options('profile',loop.profiles);options('material',loop.materials,'选择已保存的材质');
  if((material&&material.id)!==lastMaterial){lastMaterial=material&&material.id;if(material)$('material').value=material.id}
  txt('materialInfo',material?material.name+' · '+(loop.profiles.find(p=>p.id===material.profile_id)||{}).name:'请先建立或选择材质');
  txt('conditionsInfo',material?material.conditions:'记录输入来源、固定位置与光照；照片回放请如实注明。');
  txt('calibrationState',!material?'未选择材质':run&&run.revoked?'标定已失效，请重新核验':calibrated?'本批工位核验已封存':'尚未完成工位核验');
  txt('calibrationProgress',run?'不同良品 '+run.normal_checks+'/3 · 已知缺陷 '+run.defect_checks+'/1 · 不一致 '+run.failed_checks+' 张':'至少3张不同良品和1张已知缺陷，全部结果一致后才能封存。');
  txt('calibrationReason',run&&run.revoke_reason?run.revoke_reason:'工位核验不等于独立准确率认证；换花色需使用对应的冻结参照。');
  const cert=run&&run.certificate;
  if((run&&run.id)!==lastRun||(cert&&cert.id)!==lastCertificate){lastRun=run&&run.id;lastCertificate=cert&&cert.id;$('purpose').value=calibrated?'inspection':'calibration_good';$('conditionsConfirmed').checked=false}
  const samples=s.samples.filter(row=>!material||!row.profile_id_hint||row.profile_id_hint===material.profile_id);
  options('sample',samples);
  if((cycle&&cycle.id)!==lastCycle||(result&&result.id)!==lastResult){lastCycle=cycle&&cycle.id;lastResult=result&&result.id;$('held').checked=false;$('confirmed').checked=false;$('verdict').value='';$('reviewNote').value=''}
  if(result)$('held').checked=true;
  let step=!calibrated||phase==='CONFIGURING'?0:['STOPPED','INSPECTING'].includes(phase)?1:holds.includes(phase)||phase==='CONFIRMING'?2:isIdle&&cycle?3:1;
  for(let i=0;i<4;i++)$('step'+i).className='step '+(i===step?'active':i<step?'done':'');
  $('progress').className='progress '+(busy?'busy':'');
  const imageBase=cycle?'/image?cycle='+cycle.id+'&kind=':null;
  img('input',imageBase?imageBase+'input':null);img('result',result?imageBase+view:null);$('inputEmpty').hidden=!!cycle;$('resultEmpty').hidden=!!result;
  txt('decision',result?(result.pl_image_alarm?'FPGA 缺陷':'FPGA 正常'):'—');
  txt('reviewDecision',review?'人工复核：'+verdictNames[review.verdict]+' · '+review.operator:'尚未记录人工复核');
  txt('engine',result?(result.pl_engine_seconds*1000).toFixed(1):'—');txt('wall',result?(result.wall_seconds*1000).toFixed(1):'—');txt('sequence',result?result.pl_frame_sequence:'—');
  $('selectMaterial').disabled=busy||!isIdle||!$('material').value;
  $('createMaterial').disabled=busy||!isIdle||!actor||!$('materialName').value.trim()||!$('conditions').value.trim();
  $('freeze').disabled=busy||!isIdle||!run||!run.ready_to_freeze||!actor||!$('conditionsConfirmed').checked;
  $('restart').disabled=busy||!isIdle||!material||!$('restartReason').value.trim();
  for(const id of ['material','profile','materialName','conditions','restartReason'])$(id).disabled=busy||!isIdle;
  $('sample').disabled=busy||!isIdle||!material;$('purpose').disabled=$('sample').disabled;
  $('load').disabled=$('sample').disabled||!$('sample').value||($('purpose').value==='inspection'&&(!calibrated||!$('conditionsConfirmed').checked));
  $('upload').disabled=busy||!isIdle||!material;
  $('inspect').disabled=busy||phase!=='STOPPED'||!$('held').checked;
  $('review').disabled=busy||!holds.includes(phase)||!!review||!actor||!$('verdict').value;
  $('verdict').disabled=busy||!holds.includes(phase)||!!review;$('reviewNote').disabled=$('verdict').disabled;
  $('release').disabled=busy||phase!=='GOOD_HOLD'||!review||!calibrated||!$('confirmed').checked||!actor;
  $('segregate').disabled=busy||!holds.includes(phase)||phase==='GOOD_HOLD'||!review||!$('confirmed').checked||!actor;
  txt('segregate',cycle&&cycle.purpose!=='inspection'?'完成并记录该核验样本':phase==='DEFECT_HOLD'?'确认缺陷件隔离':'确认移出待定／冲突工件');
  $('reset').disabled=busy||phase!=='FAULT'||!$('confirmed').checked;
  txt('identity','参照：'+(material?material.profile_id:'—')+'\n启动编号：'+(s.connection?s.connection.boot_identity:'—')+'\n启动配置频率：'+(s.deployment&&s.deployment.runtime_clock?s.deployment.runtime_clock.pl_clock_mhz+' MHz':'未记录')+'\n标定凭证：'+(cert?cert.id:'未封存')+'\n本次结果：'+(result?result.id:'—'));
  $('events').replaceChildren();for(const event of [...s.events].reverse()){const row=document.createElement('div');row.className='event';const time=document.createElement('time'),value=document.createElement('span');time.textContent=new Date(event.utc).toLocaleTimeString();value.textContent=(eventNames[event.event]||event.event)+(event.reason?' · '+event.reason:'');row.append(time,value);$('events').append(row)}
  $('counts').replaceChildren();for(const [key,label]of Object.entries({inspected:'FPGA检测次数',calibration_samples:'已复核核验样本',calibration_failed:'核验不一致',manual_reviews:'人工复核记录',conflicts:'生产复核冲突',released:'确认放行',segregated:'确认隔离',unvalidated_removed:'待定／冲突移出',faults:'故障'})){const row=document.createElement('div');row.className='row';const a=document.createElement('span'),b=document.createElement('b');a.textContent=label;b.textContent=s.counts[key]||0;row.append(a,b);$('counts').append(row)}
  const link=$('sourceLink'),safe=cycle&&/^https?:\/\//.test(cycle.source_url||'');link.hidden=!safe;if(safe)link.href=cycle.source_url;
  if(s.error)error(s.error);
  if(isIdle&&s.revision!==lastAuditRevision){lastAuditRevision=s.revision;loadAudit()}
}
async function poll(){try{const response=await fetch('/api/state');if(!response.ok)throw Error('工作站暂不可用');render(await response.json())}catch(e){error(e.message);txt('connection','工作站连接中断');for(const button of document.querySelectorAll('button'))button.disabled=true}}
async function act(op,extra={}){
  if(!state||pending)return;pending=true;error('');const body={op,session:state.session,revision:state.revision,operator:$('operator').value.trim(),sample_id:$('sample').value,purpose:$('purpose').value,conditions_confirmed:$('conditionsConfirmed').checked,input_held_confirmed:$('held').checked,operator_confirmed:$('confirmed').checked,result_id:state.cycle&&state.cycle.result&&state.cycle.result.id,...extra};render(state);
  try{const response=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(data.error||'操作失败');if(['review','release','segregate','load','reset_fault'].includes(op))$('confirmed').checked=false;render(data)}catch(e){error(e.message)}finally{pending=false;await poll()}
}
async function loadAudit(){
  try{const response=await fetch('/api/audit');if(!response.ok)return;const data=await response.json();$('auditRows').replaceChildren();for(const item of data.records.slice(-12).reverse()){const tr=document.createElement('tr');for(const value of [new Date(item.loaded_utc).toLocaleTimeString(),item.material,purposeNames[item.purpose],item.fpga_alarm==null?'—':item.fpga_alarm?'缺陷':'正常',verdictNames[item.review]||'未复核',item.review_operator||'—',dispositionNames[item.disposition]||phaseNames[item.phase]||'未完成']){const td=document.createElement('td');td.textContent=value||'—';tr.append(td)}$('auditRows').append(tr)}}catch(e){txt('auditStatus','追溯记录暂不可用，可稍后刷新')}
}
$('selectMaterial').onclick=()=>act('select_material',{material_id:$('material').value});
$('createMaterial').onclick=()=>act('create_material',{name:$('materialName').value,profile_id:$('profile').value,conditions:$('conditions').value});
$('freeze').onclick=()=>act('freeze_calibration');$('restart').onclick=()=>act('restart_calibration',{reason:$('restartReason').value});
$('load').onclick=()=>act('load');$('inspect').onclick=()=>act('inspect');$('review').onclick=()=>act('review',{verdict:$('verdict').value,note:$('reviewNote').value});
$('release').onclick=()=>act('release');$('segregate').onclick=()=>act('segregate');$('reset').onclick=()=>act('reset_fault');
for(const id of ['operator','materialName','conditions','restartReason','verdict','reviewNote','purpose','conditionsConfirmed','held','confirmed','material'])$(id).addEventListener('input',()=>state&&render(state));
$('overlayTab').onclick=()=>{view='overlay';state&&render(state)};$('maskTab').onclick=()=>{view='mask';state&&render(state)};
$('upload').onclick=()=>$('file').click();$('file').onchange=async()=>{const file=$('file').files[0];if(!file||pending)return;pending=true;error('');render(state);try{const response=await fetch('/api/upload',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-File-Name':encodeURIComponent(file.name)},body:file});const data=await response.json();if(!response.ok)throw Error(data.error||'导入失败');render(data.state);$('sample').value=data.sample_id}catch(e){error(e.message)}finally{pending=false;$('file').value='';await poll()}};
for(const button of document.querySelectorAll('button'))button.disabled=true;poll();setInterval(poll,700);
