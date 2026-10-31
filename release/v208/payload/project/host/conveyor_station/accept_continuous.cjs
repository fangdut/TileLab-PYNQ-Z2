// Live FPGA acceptance; all program-driven reviews explicitly labelled non-human.
const{chromium}=require('./browser_test_runtime.cjs').browser();
const fs=require('fs'),path=require('path'),{spawnSync}=require('child_process');
const base='http://127.0.0.1:8794',out=path.join(__dirname,'evidence_continuous');fs.mkdirSync(out,{recursive:true});
const sleep=ms=>new Promise(r=>setTimeout(r,ms)),state=async()=>fetch(base+'/api/state').then(r=>r.json());
const samples=[],records=[];let monitoring=true;
async function post(op,extra={}){const s=await state(),r=await fetch(base+'/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run:s.run,op,...extra})});const d=await r.json();if(!r.ok)throw Error(d.error);return d}
async function wait(check,seconds=40){const until=Date.now()+seconds*1000;while(Date.now()<until){const s=await state();if(s.phase==='FAULT')throw Error(s.error);if(check(s))return s;await sleep(120)}throw Error('state timeout')}
(async()=>{
 const initial=await fetch('http://127.0.0.1:8793/api/state').then(r=>r.json());
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--disable-background-timer-throttling','--disable-renderer-backgrounding']});
 const ctx=await browser.newContext({viewport:{width:1280,height:720},deviceScaleFactor:1});
 const display=await ctx.newPage(),operator=await ctx.newPage(),errors=[];
 for(const p of [display,operator])p.on('pageerror',e=>errors.push(e.message));
 await display.goto(base+'/display?replay=automation');await operator.setViewportSize({width:1440,height:1050});await operator.goto(base+'/?replay=automation');
 await operator.locator('#operator').fill('连续检测联调自动回放（非人工）');
 const framesDir=path.join(out,'frames_'+Date.now());fs.mkdirSync(framesDir);const frames=[];let recording=true;
 const recorder=(async()=>{while(recording){const t=Date.now(),file=String(frames.length).padStart(5,'0')+'.jpg';await display.screenshot({path:path.join(framesDir,file),type:'jpeg',quality:80});frames.push({file,t});await sleep(Math.max(0,140-(Date.now()-t)))}})();
 const monitor=(async()=>{while(monitoring){const s=await state();samples.push({t:Date.now(),phase:s.phase,row:s.row?.id,token:s.token,x:s.motion.x,moving:s.motion.moving,waiting:s.motion.waiting_for_result,alarm:s.cycle?.result?.pl_image_alarm});await sleep(100)}})();
 let s=await state();const queue=s.samples.slice(0,4).map(r=>r.id);
 await post('start',{queue,zone_seconds:4});
 for(let i=0;i<2;i++){
   s=await wait(s=>s.row?.id===queue[i]&&s.phase==='PASSING');
   if(s.cycle.review!==null||s.cycle.disposition.command!=='automatic_pass')throw Error('automatic pass fabricated a review');
   records.push({kind:'no_alarm_auto_pass',capture:s.capture,cycle:s.cycle});
   await display.screenshot({path:path.join(out,`0${i+1}_正常照片不停顿自动通过.png`)});
 }
 s=await wait(s=>s.row?.id===queue[2]&&s.phase==='REVIEW');
 if(s.cycle.result.pl_image_alarm!==1||Math.abs(s.motion.x-780)>1)throw Error('alarm did not stop at review zone');
 const token=s.token;await sleep(1000);if((await state()).token!==token)throw Error('alarmed tile left without review');
 await display.screenshot({path:path.join(out,'03_异常照片在复核区停下.png')});
 await operator.locator('#seen').check();await sleep(300);await operator.locator('#defect').click();
 await wait(s=>s.phase==='OUTGOING');
 s=await wait(s=>s.row?.id===queue[3]&&s.phase==='REVIEW');
 if(!await operator.locator('#seen').isChecked())throw Error('review acknowledgement reset for next tile');
 if(!s.review_ack)throw Error('server acknowledgement not retained');
 await post('pause');records.push({kind:'next_defect_waiting_ack_retained',capture:s.capture,cycle:s.cycle});
 await operator.screenshot({path:path.join(out,'04_下一张异常仍保留勾选.png')});await sleep(1800);
 recording=false;await recorder;monitoring=false;await monitor;
 const final=await fetch('http://127.0.0.1:8793/api/state').then(r=>r.json());
 if(final.counts.manual_reviews!==initial.counts.manual_reviews+1)throw Error('normal flow changed human review counter');
 for(const id of queue.slice(0,2)){
   const observations=samples.filter(r=>r.row===id&&r.phase!=='IDLE');
   if(!observations.length||observations.some(r=>r.waiting||!r.moving))throw Error('normal tile unexpectedly stopped');
 }
 if(errors.length)throw Error(errors.join(';'));
 const lines=[];for(let i=0;i<frames.length;i++){lines.push(`file '${frames[i].file}'`);lines.push('duration '+((i+1<frames.length?frames[i+1].t-frames[i].t:140)/1000).toFixed(3))}lines.push(`file '${frames.at(-1).file}'`);fs.writeFileSync(path.join(framesDir,'frames.txt'),lines.join('\n'));
 const ff=require('./browser_test_runtime.cjs').encoder();
 const encoded=spawnSync(ff,['-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',path.join(framesDir,'frames.txt'),'-fps_mode','vfr','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',path.join(out,'正常不停_异常复核_实板自动回放.mp4')],{encoding:'utf8'});
 if(encoded.status)throw Error(encoded.stderr);
 const report={scope:'V207_LIVE_FPGA_CONTINUOUS_CONVEYOR_EXPLICIT_AUTOMATION_NOT_HUMAN',checks:['two_normal_tiles_never_stopped','normal_no_human_review_record','alarmed_tile_stops_at_review_zone','alarm_waits_for_review','one_time_ack_retained_for_next_defect','normal_and_review_audit_distinct','real_canvas_capture_and_FPGA_inference'],zone_seconds:4,manual_review_delta:final.counts.manual_reviews-initial.counts.manual_reviews,automatic_pass_delta:final.counts.automatic_passed-initial.counts.automatic_passed,records,samples,video_seconds:(frames.at(-1).t-frames[0].t)/1000,browserErrors:errors};
 fs.writeFileSync(path.join(out,'acceptance.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({ok:true,phase:s.phase,frame:s.cycle.result.pl_frame_sequence,video_seconds:report.video_seconds,autoPassDelta:report.automatic_pass_delta,manualDelta:report.manual_review_delta}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
