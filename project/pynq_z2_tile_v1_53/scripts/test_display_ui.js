const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'host/workstation.html'),'utf8');
const inline=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];new vm.Script(inline);
const source=inline.split('// BEGIN STIMULUS PUBLICATION DISPLAY')[1].split('// END STIMULUS PUBLICATION DISPLAY')[0];
const els={stimulus:{},stimulusStatus:{style:{}},motionStatus:{style:{}}},context=vm.createContext({$:id=>els[id],document:{activeElement:null}});vm.runInContext(source,context);
const cases=[];
function render(value){context.value=value;vm.runInContext('renderStimulus(value)',context)}
function test(name,fn){fn();cases.push({name,passed:true})}
const old={requested:'station_0',request_id:'a'.repeat(32),observed:'station_0',observed_request_id:'a'.repeat(32),ready:true,age_seconds:.1,message:'player adopted prior request',motion:{state:'PROGRESSING',progressing:true,message:'old source progressing'}};
test('pending new source never claims published/adopted despite old READY',()=>{
 render({stimulus:'station_0',display_pending:{value:'real_video',request_id:'b'.repeat(32)},stimulus_status:old});
 assert.equal(els.stimulus.disabled,true);assert.equal(els.stimulus.value,'real_video');assert.match(els.stimulusStatus.textContent,/尚未确认命令发布/);
 assert.match(els.stimulusStatus.textContent,/当前已发布：请求 station_0/);assert.equal(els.stimulusStatus.style.color,'#a45c24');assert.match(els.motionStatus.textContent,/old source progressing/);
});
test('successful publish waits for exact player adoption',()=>{
 render({stimulus:'real_video',display_pending:null,stimulus_status:{...old,requested:'real_video',request_id:'b'.repeat(32),ready:false,message:'waiting for new request'}});
 assert.equal(els.stimulus.disabled,false);assert.equal(els.stimulus.value,'real_video');assert.doesNotMatch(els.stimulusStatus.textContent,/正在保存/);assert.equal(els.stimulusStatus.style.color,'#a45c24');
});
test('write failure leaves old source visible and retry enabled',()=>{
 render({stimulus:'station_0',display_pending:null,stimulus_status:old});assert.equal(els.stimulus.value,'station_0');assert.equal(els.stimulus.disabled,false);assert.doesNotMatch(els.stimulusStatus.textContent,/正在保存/);
});
test('focused selector is not overwritten by polling',()=>{
 context.document.activeElement=els.stimulus;els.stimulus.value='real_001';render({stimulus:'station_0',stimulus_status:old});assert.equal(els.stimulus.value,'real_001');context.document.activeElement=null;
});
test('missing telemetry stays explicitly unconfirmed',()=>{
 render({stimulus:'station_0'});assert.match(els.stimulusStatus.textContent,/未知/);assert.match(els.stimulusStatus.textContent,/等待状态/);assert.equal(els.stimulusStatus.style.color,'#a45c24');
});
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
fs.writeFileSync(path.join(root,'reports/v148/display_ui_native.json'),JSON.stringify({passed:true,cases,source_sha256:Object.fromEntries(['host/workstation.html','scripts/test_display_ui.js'].map(p=>[p,sha(p)])),scope:'Actual inline source in Node VM'},null,2));console.log(JSON.stringify({passed:true,cases:cases.length}));
