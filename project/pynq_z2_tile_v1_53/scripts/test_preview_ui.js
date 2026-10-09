// Execute the actual inline preview controller with native Node and fake HTTP.
// No browser, station, board, or real endpoint is started by these tests.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'host/workstation.html'),'utf8');
const inline=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
assert.equal(inline.length,1);new vm.Script(inline[0][1],{filename:'actual_workstation_inline.js'});
const code=inline[0][1].split('// BEGIN PREVIEW RATE CONTROL')[1].split('// END PREVIEW RATE CONTROL')[0];
const block=code.slice(code.indexOf('\n'));
const outcomes=[];
async function check(name,fn){await fn();outcomes.push({name,passed:true});}
function snapshot(rate=2,supported=true){return {preview_rate_fps:rate,preview_rate_supported:supported,preview_policy:{event_priority:true,idle_poll_ms:200,preview_requests:8,priority_requests:3,deferred_polls:19}};}
function response(value,ok=true){return {ok,json:async()=>value};}
function setup(fetcher=async()=>{throw Error('Unexpected HTTP request')},runtime={}){
 const elements={previewRate:{value:'2',disabled:true},previewRateStatus:{textContent:'',style:{}}},toasts=[],calls=[];
 const context=vm.createContext({$:id=>elements[id],AbortController,setTimeout,clearTimeout,
  toast:text=>toasts.push(text),fetch:async(...args)=>{calls.push(args);return fetcher(...args);},...runtime});
 vm.runInContext(block+'\nthis.ui={renderPreviewRate,changePreviewRate,previewRateRequest,getEpoch:()=>previewRateEpoch};',context);
 return {ui:context.ui,context,elements,toasts,calls};
}
function deferred(){let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};}

(async()=>{
 await check('actual inline JavaScript parses and selector provides 2/5/unlimited',()=>{
  assert.match(html,/<select id="previewRate"[^>]*disabled>[\s\S]*?<option value="2">[\s\S]*?<option value="5">[\s\S]*?<option value="0">/);
  assert.match(html,/FPGA 输入处理帧率估计/);assert.match(html,/人工抓拍不受此上限限制/);assert.match(html,/冻结预览仍接收报警事件/);
  assert.match(html,/轮询等待可达 200 ms，另加网络与处理时间/);
 });
 await check('server value overrides selector and counters are not claimed as measured fps',()=>{
  const s=setup();s.ui.renderPreviewRate(snapshot(5));assert.equal(s.elements.previewRate.value,'5');assert.equal(s.elements.previewRate.disabled,false);
  assert.match(s.elements.previewRateStatus.textContent,/服务端当前上限：5 帧\/秒/);
  assert.match(s.elements.previewRateStatus.textContent,/普通预览请求 8，优先请求 3/);
  assert.match(s.elements.previewRateStatus.textContent,/不是实测帧率/);
  s.ui.renderPreviewRate(snapshot(0));assert.equal(s.elements.previewRate.value,'0');assert.match(s.elements.previewRateStatus.textContent,/上限：不限/);
 });
 await check('legacy unsupported channel stays disabled and uses server unlimited value',()=>{
  const s=setup();s.ui.renderPreviewRate(snapshot(0,false));assert.equal(s.elements.previewRate.value,'0');assert.equal(s.elements.previewRate.disabled,true);
  assert.match(s.elements.previewRateStatus.textContent,/不支持预览限速/);
 });
 await check('missing or invalid server fields never confirm a selected setting',()=>{
  for(const bad of [{},snapshot('2'),snapshot(9),snapshot(2,1)]){
   const s=setup();s.ui.renderPreviewRate(bad);assert.equal(s.elements.previewRate.disabled,true);assert.match(s.elements.previewRateStatus.textContent,/未确认任何新档位/);
  }
 });
 await check('valid selection sends strict numeric action then reads authoritative current state',async()=>{
  const s=setup(async(url)=>url==='/api/action'?response({ok:true}):response(snapshot(5)));
  s.ui.renderPreviewRate(snapshot(2));s.elements.previewRate.value='5';await s.ui.changePreviewRate('5');
  assert.equal(s.calls.length,2);assert.deepEqual(JSON.parse(s.calls[0][1].body),{op:'preview_rate',value:5});
  assert.equal(s.calls[1][0],'/api/live');assert.equal(s.calls[1][1].cache,'no-store');
  assert.equal(s.elements.previewRate.value,'5');assert.equal(s.elements.previewRate.disabled,false);
 });
 await check('failed action response restores the service value instead of optimistic selection',async()=>{
  const s=setup(async(url)=>url==='/api/action'?response({error:'Injected reject'},false):response(snapshot(2)));
  s.ui.renderPreviewRate(snapshot(2));s.elements.previewRate.value='5';await s.ui.changePreviewRate('5');
  assert.equal(s.elements.previewRate.value,'2');assert.equal(s.elements.previewRate.disabled,false);
  assert.match(s.elements.previewRateStatus.textContent,/设置请求未确认/);assert.match(s.toasts[0],/Injected reject/);
 });
 await check('lost action response still adopts a successful server-side update from readback',async()=>{
  const s=setup(async(url)=>{if(url==='/api/action')throw Error('Connection lost after write');return response(snapshot(5));});
  s.ui.renderPreviewRate(snapshot(2));await s.ui.changePreviewRate('5');assert.equal(s.elements.previewRate.value,'5');
  assert.match(s.elements.previewRateStatus.textContent,/重新读取服务端当前值/);
 });
 await check('failed action and readback recover last confirmed value with explicit uncertainty',async()=>{
  const s=setup(async()=>{throw Error('Offline');});s.ui.renderPreviewRate(snapshot(2));s.elements.previewRate.value='5';await s.ui.changePreviewRate('5');
  assert.equal(s.elements.previewRate.value,'2');assert.equal(s.elements.previewRate.disabled,false);
  assert.match(s.elements.previewRateStatus.textContent,/服务端当前值未能确认/);assert.match(s.elements.previewRateStatus.textContent,/最近确认上限：2/);
  assert.doesNotMatch(s.elements.previewRateStatus.textContent,/服务端当前上限/);
 });
 await check('late polls from before and during change cannot undo newly confirmed value',async()=>{
  const gate=deferred();const s=setup(async(url)=>url==='/api/action'?(await gate.promise,response({ok:true})):response(snapshot(5)));
  s.ui.renderPreviewRate(snapshot(2));const oldEpoch=s.ui.getEpoch();s.elements.previewRate.value='5';
  const pending=s.ui.changePreviewRate('5'),duringEpoch=s.ui.getEpoch();assert.equal(s.elements.previewRate.disabled,true);
  s.ui.renderPreviewRate(snapshot(0),oldEpoch);assert.equal(s.elements.previewRate.value,'5');
  await s.ui.changePreviewRate('0');assert.equal(s.calls.length,1);
  gate.resolve();await pending;s.ui.renderPreviewRate(snapshot(2),oldEpoch);s.ui.renderPreviewRate(snapshot(0),duringEpoch);
  assert.equal(s.elements.previewRate.value,'5');assert.equal(s.elements.previewRate.disabled,false);
  s.ui.renderPreviewRate(snapshot(0),s.ui.getEpoch());assert.equal(s.elements.previewRate.value,'0');
 });
 await check('invalid selection and unsupported channel never send an action',async()=>{
  const s=setup();s.ui.renderPreviewRate(snapshot(2));await s.ui.changePreviewRate('9');assert.equal(s.calls.length,0);
  s.ui.renderPreviewRate(snapshot(0,false));await s.ui.changePreviewRate('2');assert.equal(s.calls.length,0);
 });
 await check('timed-out request is reported and bounded timer is cleared',async()=>{
  let timeout,delay;const cleared=[];
  const s=setup((url,options)=>new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>{
   const error=Error('aborted');error.name='AbortError';reject(error);
  })),{setTimeout:(fn,ms)=>{timeout=fn;delay=ms;return 17;},clearTimeout:id=>cleared.push(id)});
  const request=s.ui.previewRateRequest('/fixture');assert.equal(delay,5000);timeout();
  await assert.rejects(()=>request,/预览设置请求超时/);assert.deepEqual(cleared,[17]);
 });
 const result={passed:true,tests:outcomes.length,cases:outcomes,actual_inline_script_syntax:true,
  hardware_access:false,html_sha256:crypto.createHash('sha256').update(html).digest('hex')};
 const out=path.join(root,'reports/v148');fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,'preview_ui_native.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify(result));
})().catch(error=>{console.error(error);process.exitCode=1;});
