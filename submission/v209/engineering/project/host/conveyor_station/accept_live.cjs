// Explicitly labelled automation; this is not a human review or accuracy test.
const {chromium}=require('./browser_test_runtime.cjs').browser();
const fs=require('fs'),path=require('path'),{spawnSync}=require('child_process');
const base='http://127.0.0.1:8794';
const out=path.join(__dirname,'evidence');fs.mkdirSync(out,{recursive:true});
const records=[];
const state=async()=>fetch(base+'/api/state').then(r=>r.json());
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function wait(check,seconds=35){const until=Date.now()+seconds*1000;while(Date.now()<until){const s=await state();if(s.phase==='FAULT')throw Error(s.error);if(check(s))return s;await sleep(200)}throw Error('state timeout')}
async function post(op,extra={}){const s=await state();const r=await fetch(base+'/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run:s.run,op,...extra})});const data=await r.json();if(!r.ok)throw Error(data.error);return data}
(async()=>{
 if((await state()).ui_version>=207)throw Error('Historical V206 acceptance only; use accept_continuous.cjs for V207.');
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const ctx=await browser.newContext({viewport:{width:1280,height:720},deviceScaleFactor:1});
 const display=await ctx.newPage();let errors=[];
 display.on('pageerror',e=>errors.push(e.message));
 await display.goto(base+'/display?replay=automation');
 const operator=await ctx.newPage();await operator.setViewportSize({width:1440,height:1050});
 operator.on('pageerror',e=>errors.push(e.message));
 await operator.goto(base+'/?replay=automation');
 await operator.locator('#operator').fill('联动验收自动回放（非人工）');
 let s=await state();
 if(s.phase==='REVIEW'){
   await operator.locator('#seen').check();
   await operator.locator(s.cycle.result.pl_image_alarm?'#defect':'#good').click();
   await wait(s=>s.phase==='IDLE');
 }
 s=await state();const queue=[s.samples[0].id,s.samples[2].id];
 // Real browser screenshots sampled at ~10 Hz, then encoded with measured
 // timestamps. No accelerated inference, synthetic mask, or cut-out wait.
 const framesDir=path.join(out,'recording_frames_'+Date.now());fs.mkdirSync(framesDir);
 const frames=[];let recording=true;
 const recorder=(async()=>{while(recording){const t=Date.now();const file=String(frames.length).padStart(5,'0')+'.jpg';await display.screenshot({path:path.join(framesDir,file),type:'jpeg',quality:82});frames.push({file,t});await sleep(Math.max(0,100-(Date.now()-t)))}})();
 await post('start',{queue,incoming:6});
 await wait(s=>s.phase==='MOVING');
 // Capture with a stale token cannot enter the FPGA pipeline.
 let bad=await fetch(base+'/api/capture',{method:'POST',headers:{'X-Capture-Token':'stale'},body:Buffer.from('invalid')});
 if(bad.status!==409)throw Error('stale capture was accepted');
 s=await wait(s=>s.phase==='REVIEW'&&s.row?.id===queue[0]);
 if(s.cycle.result.pl_image_alarm!==0)throw Error('normal source alarmed; stop without overriding');
 const first=s.cycle.result.pl_frame_sequence;
 records.push({stage:'normal_captured_and_detected',capture:s.capture,cycle:s.cycle});
 await display.screenshot({path:path.join(out,'01_正常瓷砖_FPGA检测.png')});
 // Same capture token is idempotent after a result; it must not infer twice.
 let duplicate=await fetch(base+'/api/capture',{method:'POST',headers:{'X-Capture-Token':s.token},body:Buffer.from('duplicate')});
 if(!duplicate.ok||(await state()).cycle.result.pl_frame_sequence!==first)throw Error('duplicate inference');
 // Stale result cannot be reviewed.
 let rejected=false;try{await post('review',{result_id:'stale',operator:'联调自动回放（非人工）',verdict:'good',confirmed:true})}catch(e){rejected=true}if(!rejected)throw Error('stale review accepted');
 await operator.locator('#seen').check();await operator.locator('#good').click();
 await wait(s=>s.phase==='OUTGOING');
 await display.screenshot({path:path.join(out,'02_复核后放行_自动回放.png')});
 s=await wait(s=>s.phase==='MOVING'&&s.row?.id===queue[1]);
 if(s.cycle)throw Error('old cycle leaked into new tile');
 await display.screenshot({path:path.join(out,'03_裂纹瓷砖缓速入线.png')});
 s=await wait(s=>s.phase==='REVIEW'&&s.row?.id===queue[1]);
 if(s.cycle.result.pl_image_alarm!==1)throw Error('crack source not alarmed');
 if(s.cycle.result.pl_frame_sequence!==first+1)throw Error('unexpected frame progression');
 await post('pause');
 records.push({stage:'crack_captured_and_detected_awaiting_human',capture:s.capture,cycle:s.cycle});
 await sleep(500);
 await display.screenshot({path:path.join(out,'04_裂纹瓷砖_FPGA标记_待复核.png')});
 await operator.screenshot({path:path.join(out,'05_电脑端同步复核界面.png')});
 await sleep(2500);recording=false;await recorder;
 const lines=[];for(let i=0;i<frames.length;i++){lines.push(`file '${frames[i].file}'`);lines.push('duration '+((i+1<frames.length?frames[i+1].t-frames[i].t:100)/1000).toFixed(3))}lines.push(`file '${frames.at(-1).file}'`);
 fs.writeFileSync(path.join(framesDir,'frames.txt'),lines.join('\n'));
 const ff=require('./browser_test_runtime.cjs').encoder();
 const encoded=spawnSync(ff,['-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',path.join(framesDir,'frames.txt'),'-fps_mode','vfr','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',path.join(out,'联动流水线_实板自动回放.mp4')],{encoding:'utf8'});
 if(encoded.status!==0)throw Error('encode failed: '+encoded.stderr);
 fs.writeFileSync(path.join(out,'recording_timing.json'),JSON.stringify({scope:'REAL_BROWSER_SCREENSHOTS_MEASURED_WALL_TIME_NOT_ACCELERATED',frames:frames.length,duration_seconds:(frames.at(-1).t-frames[0].t)/1000,framesDir},null,2));
 if(errors.length)throw Error('browser errors: '+errors.join(';'));
 fs.writeFileSync(path.join(out,'acceptance.json'),JSON.stringify({scope:'LIVE_FPGA_BROWSER_CANVAS_CAPTURE_AUTOMATION_NOT_HUMAN_NOT_INDEPENDENT_ACCURACY',checks:['stale_capture_rejected','native_rgb_pixel_identity','same_cycle_mask','stale_review_rejected','duplicate_capture_no_extra_inference','normal_frame_and_crack_frame_real_FPGA','old_result_cleared_before_next_tile','review_required_before_leave','final_crack_held_for_human'],records,browserErrors:errors},null,2));
 console.log(JSON.stringify({ok:true,firstFrame:first,finalFrame:s.cycle.result.pl_frame_sequence,phase:s.phase,output:out}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
