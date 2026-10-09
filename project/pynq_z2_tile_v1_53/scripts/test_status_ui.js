// Execute the production refresh glue and channel implementation, including
// delayed/out-of-order body completion. No board, service or browser required.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'host/workstation.html'),'utf8'),channel=fs.readFileSync(path.join(root,'host/status_channel.js'),'utf8');
const inline=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];new vm.Script(inline);
const glue=inline.split('// BEGIN LIVE AND ARCHIVE REFRESH')[1].split('// END LIVE AND ARCHIVE REFRESH')[0];
assert.ok(html.includes('<script src="/status_channel.js"></script>'));
assert.ok(!inline.includes("fetch('/api/state"));assert.ok(!inline.includes("previewRateRequest('/api/state"));
const cases=[];
function fixture(){
 const requests=[],els=new Proxy({}, {get:(o,k)=>o[k]??=( {value:k==='filter'||k==='archiveKind'?'all':'',style:{},textContent:''})});
 const ctx=vm.createContext({URLSearchParams,AbortController,Error,setTimeout,clearTimeout,Date,Number,Math,
  $:id=>els[id],state:null,previewRateEpoch:0,previewRatePending:false,previewRateWarning:'',previewRateUncertain:false,pageOffset:0,
  render:()=>{},updatePreviewIdentity:()=>{},renderCards:()=>{},renderArchiveInventory:v=>ctx.inventory=v,
  fetch:(url,options)=>new Promise((resolve,reject)=>{requests.push({url,options,resolve:(value,ok=true)=>resolve({ok,json:async()=>value}),reject})})});
 vm.runInContext(channel+'\n'+glue,ctx);const run=code=>vm.runInContext(code,ctx);
 return {ctx,els,requests,run};
}
async function flush(){await new Promise(r=>setImmediate(r))}
async function test(name,fn){await fn();cases.push({name,passed:true})}
async function main(){
 await test('live state refresh completes while archive is pending; late archive cannot restore old enabled state',async()=>{
  const f=fixture();let a=f.run('refreshArchive()'),l=f.run('refresh()');assert.equal(f.requests.length,2);
  f.requests[1].resolve({enabled:false,storage:{mode:'preview',max_bytes:20}});await l;assert.equal(f.ctx.state.enabled,false);
  f.requests[0].resolve({enabled:true,records:[],records_total:0,archive:{pending:3},storage_inventory:{used_bytes:30,max_bytes:100,mode:'archive'}});await a;
  assert.equal(f.ctx.state.enabled,false);assert.equal(f.els.nPending.textContent,3);assert.equal(f.ctx.inventory.mode,'preview');assert.equal(f.ctx.inventory.at_limit,true);
 });
 await test('same channel coalesces polls and archive errors do not label live connection offline',async()=>{
  const f=fixture();const a=f.run('refreshArchive()'),b=f.run('refreshArchive()');assert.equal(a,b);assert.equal(f.requests.length,1);
  f.els.connection.textContent='live connected';f.requests[0].resolve({error:'Archive is busy'},false);await a;
  assert.equal(f.els.connection.textContent,'live connected');assert.match(f.els.archiveRefresh.textContent,/Archive is busy/);assert.equal(f.els.nPending.textContent,'—');
 });
 await test('changed filter rejects an old response even when aborted fetch still delivers; old finally cannot clear new request',async()=>{
  const f=fixture();let a=f.run('refreshArchive()');f.els.filter.value='confirmed_crack';let b=f.run('refreshArchive()');assert.equal(f.requests.length,2);assert.ok(f.requests[0].options.signal.aborted);
  f.requests[0].resolve({records:[{id:'wrong'}],archive:{pending:99}});await a;assert.equal(f.run('archiveState'),null);
  const again=f.run('refreshArchive()');assert.equal(again,b);assert.equal(f.requests.length,2);
  f.requests[1].resolve({records:[],records_total:0,archive:{pending:0}});await b;assert.equal(f.els.nPending.textContent,0);
 });
 await test('invalidated action-era live reply cannot overwrite newer control intent',async()=>{
  const f=fixture();let a=f.run('refresh()');f.run('liveChannel.invalidate()');let b=f.run('refresh()');
  f.requests[1].resolve({enabled:false});await b;f.requests[0].resolve({enabled:true});await a;assert.equal(f.ctx.state.enabled,false);
 });
 await test('old-filter failures cannot replace current successful result',async()=>{
  const f=fixture();let a=f.run('refreshArchive()');f.els.search.value='new';let b=f.run('refreshArchive()');
  f.requests[1].resolve({records:[],records_total:0,archive:{pending:4}});await b;f.requests[0].reject(Error('old failure'));await a;
  assert.equal(f.els.nPending.textContent,4);assert.doesNotMatch(f.els.archiveRefresh.textContent,/old failure/);
 });
 await test('inventory age advances while list is delayed; current storage settings have priority',async()=>{
  const f=fixture();f.ctx.state={storage:{max_bytes:40,mode:'preview'}};
  f.run("archiveState={storage_inventory:{used_bytes:50,max_bytes:100,snapshot_age_seconds:2,snapshot_stale:false}};archiveReceivedAt=Date.now()-10000;archiveMessage='busy';renderArchive()");
  assert.ok(f.ctx.inventory.snapshot_age_seconds>=12);assert.equal(f.ctx.inventory.snapshot_stale,true);assert.equal(f.ctx.inventory.at_limit,true);
  assert.match(f.els.archiveRefresh.textContent,/该次快照/);
 });
 await test('preview-rate poll epoch is captured at request start',async()=>{
  const f=fixture();let epoch;f.ctx.render=e=>epoch=e;f.ctx.previewRateWarning='keep';const a=f.run('refresh()');f.ctx.previewRateEpoch=2;
  f.requests[0].resolve({enabled:false});await a;assert.equal(epoch,0);assert.equal(f.ctx.previewRateWarning,'keep');
 });
 await test('bounded timeout clears channel and allows a later recovery without an unhandled rejection',async()=>{
  const f=fixture();f.ctx.fetch=(url,opts)=>new Promise((resolve,reject)=>opts.signal.addEventListener('abort',()=>reject(Object.assign(Error('abort'),{name:'AbortError'}))));
  f.run('archiveChannel.timeout=20');await f.run('refreshArchive()');assert.match(f.els.archiveRefresh.textContent,/超时/);assert.equal(f.run('archiveChannel.active'),null);
  f.ctx.fetch=async()=>({ok:true,json:async()=>({records:[],records_total:0,archive:{pending:0}})});await f.run('refreshArchive()');assert.doesNotMatch(f.els.archiveRefresh.textContent,/超时/);
 });
 const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
 const out={passed:true,cases,source_sha256:Object.fromEntries(['host/status_channel.js','host/workstation.html','scripts/test_status_ui.js'].map(p=>[p,sha(p)])),scope:'Production JavaScript in Node VM; not a visual browser or hardware test'};
 fs.writeFileSync(path.join(root,'reports/v148/status_ui_native.json'),JSON.stringify(out,null,2));console.log(JSON.stringify({passed:true,cases:cases.length}));
}
main().catch(error=>{console.error(error);process.exitCode=1});
