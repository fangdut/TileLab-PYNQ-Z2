"""Live full-loop soak with explicit automated review; no accuracy certification.

Never retries an inspection or auto-recovers a fault. Stops at the first failed
cycle, preserving the plan, partial records, serial trace and API state.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,statistics,threading,time,urllib.request

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--cycles',type=int,default=100);p.add_argument('--review-hold',type=float,default=.25);p.add_argument('--serial');p.add_argument('--url',default='http://127.0.0.1:8793');a=p.parse_args()
    if a.cycles<1 or a.review_hold<0:p.error('Invalid soak length or hold')
    if not (a.runtime/'events.jsonl').is_file() or not (a.runtime/'cycles').is_dir():p.error('--runtime must be the station records directory containing events.jsonl and cycles/')
    a.out.mkdir(parents=True,exist_ok=False);records=[];stop=threading.Event();serial_errors=[]
    actor='连续闭环自动验收（公开照片标签模拟复核，非真实人工）'
    def save(name,data):
        dest=a.out/name;tmp=dest.with_suffix(dest.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');tmp.replace(dest)
    def request(path,body=None):
        req=urllib.request.Request(a.url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)
    def state():return request('/api/state')
    def act(op,**values):
        s=state();return request('/api/action',dict(op=op,session=s['session'],revision=s['revision'],operator=actor,**values))
    def wait():
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            s=state()
            if s['phase'] not in ['CONFIGURING','INSPECTING','CONFIRMING']:return s
            time.sleep(.04)
        raise TimeoutError('Station worker deadline')
    serial_port=None;serial_thread=None
    if a.serial:
        import serial
        serial_port=serial.Serial(a.serial,115200,timeout=.2)
        def monitor():
            try:
                with (a.out/'uart.jsonl').open('a',encoding='utf8') as stream:
                    while not stop.is_set():
                        data=serial_port.read(4096)
                        if data:stream.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),hex=data.hex(),text=data.decode('utf8',errors='replace')))+'\n');stream.flush()
            except Exception as error:serial_errors.append(repr(error))
        serial_thread=threading.Thread(target=monitor,daemon=True);serial_thread.start()
    start=time.perf_counter();passed=False;error=None;baselines={}
    try:
        initial=state();save('initial.json',initial)
        assert initial['phase'] in ['READY','RELEASED','SEGREGATED','REMOVED'] and initial['closed_loop']['calibrated']
        material=initial['closed_loop']['active_material'];profile=material['profile_id'];session=initial['session'];boot=initial['connection']['boot_identity'];faults=initial['counts']['faults']
        expected=json.loads(a.expected.read_text());available={r['id'] for r in initial['samples']}
        groups={alarm:sorted(k for k,v in expected.items() if k in available and v['profile_id']==profile and v['expected_alarm']==alarm) for alarm in [0,1]}
        assert all(groups.values());indices={0:0,1:0};plan=[]
        for i in range(a.cycles):
            alarm=i%2;sample=groups[alarm][indices[alarm]%len(groups[alarm])];indices[alarm]+=1;plan.append(dict(index=i+1,sample_id=sample,expected_alarm=alarm))
        save('plan.json',dict(scope='FULL_LOGICAL_STOP_INSPECT_REVIEW_DISPOSE_SOAK_NOT_ACCURACY',selected_before_inference=plan,boot_identity=boot,model_sha256=material['profile_sha256'],review_hold_seconds=a.review_hold,extra_intercycle_pause_seconds=0,inspection_retries=0,automatic_recovery=False,actor=actor,physical_actuation=False,real_human_review=False))
        last_frame=None;seen=set()
        for row in plan:
            tick=time.perf_counter();act('load',sample_id=row['sample_id'],purpose='inspection',conditions_confirmed=True)
            act('inspect',input_held_confirmed=True);s=wait()
            assert s['phase']=='REVIEW_HOLD',dict(phase=s['phase'],error=s['error'])
            cycle=s['cycle'];result=cycle['result'];assert cycle['id'] not in seen;seen.add(cycle['id'])
            assert s['session']==session and result['boot_identity']==boot and result['model_sha256']==material['profile_sha256']
            assert result['pl_image_alarm']==row['expected_alarm'] and not result['cpu_detection'] and not result['gpu_detection']
            frame=result['pl_frame_sequence']
            if last_frame is not None:assert frame==(last_frame+1)&0xffffffff
            last_frame=frame
            raw=(a.runtime/'cycles'/cycle['id']/'fpga/raw_result.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()==result['result_sha256']
            normalized=bytearray(raw);normalized[36:40]=bytes(4);digest=hashlib.sha256(normalized).hexdigest()
            key=row['sample_id']
            if key in baselines:assert digest==baselines[key],'Repeated PL score/mask changed'
            else:baselines[key]=digest
            hold_start=time.perf_counter();time.sleep(a.review_hold)
            act('review',result_id=result['id'],verdict='defect' if row['expected_alarm'] else 'good',note='已知公开标签驱动的连续流程测试；非真实人工复核，不计为独立准确率')
            op='segregate' if row['expected_alarm'] else 'release';act(op,result_id=result['id'],operator_confirmed=True);s=wait()
            assert s['phase']==('SEGREGATED' if row['expected_alarm'] else 'RELEASED'),s
            assert s['cycle']['id']==cycle['id'] and s['cycle']['disposition']['result_id']==result['id'] and s['cycle']['disposition']['command']==op
            assert s['counts']['faults']==faults and s['closed_loop']['calibrated'] and s['connection']['boot_identity']==boot
            records.append(dict(**row,cycle_id=cycle['id'],result_id=result['id'],frame_sequence=frame,boot_identity=boot,model_sha256=result['model_sha256'],raw_sha256=result['result_sha256'],normalized_payload_sha256=digest,pl_seconds=result['pl_engine_seconds'],transfer_detection_seconds=result['wall_seconds'],cycle_seconds=time.perf_counter()-tick,review_and_confirmation_seconds=time.perf_counter()-hold_start,disposition=op))
            save('records.json',records);print('FULL_LOOP',len(records),'OF',a.cycles,flush=True)
        audit=request('/api/audit');selected=[r for r in audit['records'] if r['cycle_id'] in seen];assert len(selected)==a.cycles and all(r['review_operator']==actor and r['confirmed_by']==actor for r in selected)
        save('audit.json',dict(scope=audit['scope'],records=selected));save('final.json',state());passed=True
    except Exception as exc:
        error=repr(exc)
        try:save('failure_state.json',state())
        except Exception as second:save('api_failure.json',dict(error=repr(second)))
        raise
    finally:
        stop.set()
        if serial_thread:serial_thread.join(2)
        if serial_port:serial_port.close()
        summary=dict(scope='PHYSICAL_FPGA_FULL_LOGICAL_CLOSED_LOOP_SOAK_NOT_INDEPENDENT_ACCURACY_OR_PHYSICAL_ACTUATION',passed=passed,requested_cycles=a.cycles,completed_cycles=len(records),elapsed_seconds=time.perf_counter()-start,error=error,serial_errors=serial_errors,review_hold_seconds=a.review_hold,extra_intercycle_pause_seconds=0,real_human_review=False,cpu_detection=False,gpu_detection=False,automatic_recovery=False,inspection_retries=0)
        if records:
            for key in ['pl_seconds','transfer_detection_seconds','cycle_seconds']:
                values=sorted(r[key] for r in records);summary[key]=dict(mean=statistics.mean(values),maximum=max(values),p95=values[min(len(values)-1,int(.95*len(values)))])
            summary.update(boot_identity=records[0]['boot_identity'],released=sum(r['disposition']=='release' for r in records),segregated=sum(r['disposition']=='segregate' for r in records),consecutive_frames=True,repeated_payloads_identical=True)
        save('summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
