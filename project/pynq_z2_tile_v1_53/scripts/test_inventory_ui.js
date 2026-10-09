// Execute production snapshot rendering. No browser, service, or board is started.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'host/workstation.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];assert.equal(scripts.length,1);new vm.Script(scripts[0][1]);
assert.match(html,/id="storageSnapshot" role="status"/);
const source=scripts[0][1].split('// BEGIN ARCHIVE INVENTORY DISPLAY')[1].split('// END ARCHIVE INVENTORY DISPLAY')[0];
const elements={storageUsage:{textContent:''},storageSnapshot:{textContent:'',style:{}},storageInventory:{textContent:'',style:{}}};
const context=vm.createContext({$:key=>elements[key]});vm.runInContext(source,context);
const cases=[];
const observed='2026-09-29T00:00:00+00:00';
function snapshot(changes={}){return {scan_complete:true,used_bytes:1048576,auxiliary_bytes:524288,max_archive_mib:1024,free_disk_bytes:10*1073741824,not_archived_events:0,unindexed_png_count:0,temp_file_count:0,scan_issue_count:0,snapshot_age_seconds:.1,snapshot_cached:false,snapshot_stale:false,snapshot_observed_at:observed,snapshot_refresh_error:'',...changes};}
function render(value){context.snapshot=value;vm.runInContext('renderArchiveInventory(snapshot)',context);}
function run(name,value,check){render(value);check();cases.push({name,passed:true});}
run('fresh complete scan labels disk space by its observation time',snapshot(),()=>{
 assert.match(elements.storageUsage.textContent,/最近盘点占用 1.0 MiB/);assert.match(elements.storageUsage.textContent,/盘点时磁盘空闲 10.0 GiB/);
 assert.doesNotMatch(elements.storageUsage.textContent,/当前磁盘空闲/);assert.match(elements.storageSnapshot.textContent,/0.1 秒前（状态返回时）/);
 assert.match(elements.storageSnapshot.textContent,/本次刷新/);assert.ok(elements.storageSnapshot.textContent.includes(observed));
 assert.equal(elements.storageSnapshot.style.color,'');assert.match(elements.storageInventory.textContent,/目录统计不等于图像内容校验/);
});
run('cached age is taken from backend without resetting observation time',snapshot({snapshot_cached:true,snapshot_age_seconds:3.2}),()=>{
 assert.match(elements.storageSnapshot.textContent,/3.2 秒前/);assert.match(elements.storageSnapshot.textContent,/缓存展示/);
 assert.ok(elements.storageSnapshot.textContent.includes(observed));
 render(snapshot({snapshot_cached:true,snapshot_age_seconds:4.7}));assert.match(elements.storageSnapshot.textContent,/4.7 秒前/);
 assert.ok(elements.storageSnapshot.textContent.includes(observed));assert.doesNotMatch(elements.storageSnapshot.textContent,/本次刷新/);
});
run('dirty or expired complete snapshot is distinct from incomplete enumeration',snapshot({snapshot_cached:true,snapshot_stale:true,snapshot_age_seconds:7.5}),()=>{
 assert.match(elements.storageSnapshot.textContent,/快照已过期或存档已有变化/);assert.match(elements.storageSnapshot.textContent,/当前用量尚未重新确认/);
 assert.match(elements.storageInventory.textContent,/该次目录清单完成/);assert.doesNotMatch(elements.storageInventory.textContent,/该次目录清单不完整/);
 assert.equal(elements.storageSnapshot.style.color,'#a45c24');assert.match(elements.storageSnapshot.textContent,/新增留图仍会独立检查最新容量/);
});
run('refresh failure retains last values age and scan completeness',snapshot({used_bytes:2097152,scan_complete:false,scan_issue_count:3,snapshot_cached:true,snapshot_stale:true,snapshot_age_seconds:9.3,snapshot_refresh_error:'SQLite busy'}),()=>{
 assert.match(elements.storageUsage.textContent,/最近盘点已统计至少 2.0 MiB/);assert.match(elements.storageSnapshot.textContent,/9.3 秒前/);
 assert.match(elements.storageSnapshot.textContent,/刷新失败：SQLite busy/);assert.match(elements.storageSnapshot.textContent,/保留上次盘点值和原盘点时间/);
 assert.equal(elements.storageSnapshot.style.color,'#b43e39');assert.match(elements.storageInventory.textContent,/该次目录清单不完整/);
 assert.match(elements.storageInventory.textContent,/该次清点的已知下限/);assert.match(elements.storageInventory.textContent,/该次未完成项 3 个/);
 assert.match(elements.storageInventory.textContent,/重新检查仍不完整时将被阻止/);
});
run('unindexed and temporary counts are not described as recovered evidence',snapshot({unindexed_png_count:2,temp_file_count:1}),()=>{
 assert.match(elements.storageInventory.textContent,/未登记 PNG 2 个/);assert.match(elements.storageInventory.textContent,/临时文件 1 个/);
 assert.match(elements.storageInventory.textContent,/不表示已恢复证据/);assert.equal(elements.storageInventory.style.color,'#a45c24');
});
run('unknown snapshot never fabricates zero usage free space or complete scan',{},()=>{
 assert.match(elements.storageUsage.textContent,/占用 未知 MiB/);assert.match(elements.storageUsage.textContent,/磁盘空闲 未知 GiB/);
 assert.match(elements.storageUsage.textContent,/配置上限 未知 MiB/);assert.match(elements.storageInventory.textContent,/尚未确认统计是否完整/);
 assert.doesNotMatch(elements.storageInventory.textContent,/清单完成/);assert.match(elements.storageSnapshot.textContent,/快照时效尚未确认/);
});
run('invalid numeric snapshot fields display unknown rather than zero',snapshot({used_bytes:-1,free_disk_bytes:NaN,snapshot_age_seconds:-2,max_archive_mib:0}),()=>{
 assert.match(elements.storageUsage.textContent,/占用 未知 MiB/);assert.match(elements.storageUsage.textContent,/磁盘空闲 未知 GiB/);
 assert.match(elements.storageSnapshot.textContent,/快照时效尚未确认/);assert.equal(elements.storageSnapshot.style.color,'#a45c24');
});
run('configuration limit changes without pretending cached disk bytes changed',snapshot({snapshot_cached:true,snapshot_age_seconds:2,used_bytes:33554432,max_archive_mib:16,at_limit:true}),()=>{
 assert.match(elements.storageUsage.textContent,/配置上限 16 MiB/);assert.match(elements.storageUsage.textContent,/最近盘点占用 32.0 MiB/);
 assert.match(elements.storageUsage.textContent,/盘点时磁盘空闲 10.0 GiB/);assert.match(html,/最近盘点占用达到当前配置上限/);
 assert.doesNotMatch(html,/当前已有存档超出上限/);
});
run('successful refresh clears previous warning and admits a real zero observation',snapshot({used_bytes:0,auxiliary_bytes:0,snapshot_observed_at:'2026-09-29T00:00:10+00:00'}),()=>{
 assert.match(elements.storageUsage.textContent,/最近盘点占用 0.0 MiB/);assert.doesNotMatch(elements.storageSnapshot.textContent,/刷新失败|已过期/);
 assert.equal(elements.storageSnapshot.style.color,'');assert.equal(elements.storageInventory.style.color,'');
});
run('failure explanation uses bounded plain text and does not become markup',snapshot({snapshot_stale:true,snapshot_refresh_error:'<img src=x onerror=alert(1)>'+('x'.repeat(300))}),()=>{
 assert.ok(elements.storageSnapshot.textContent.includes('<img src=x onerror=alert(1)>'));assert.equal(elements.storageSnapshot.innerHTML,undefined);
 assert.ok(elements.storageSnapshot.textContent.length<600);assert.equal(elements.storageSnapshot.style.color,'#b43e39');
});
const result={passed:true,tests:cases.length,cases,html_sha256:crypto.createHash('sha256').update(html).digest('hex'),browser_rendered:false,snapshot_contract:['snapshot_age_seconds','snapshot_cached','snapshot_stale','snapshot_observed_at','snapshot_refresh_error']};
const out=path.join(root,'reports/v148');fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,'inventory_ui_native.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({passed:true,tests:cases.length}));
