# SPDX-License-Identifier: MIT
"""Constant-speed capture zone; only alarmed/late tiles stop at review."""
from pathlib import Path
import datetime,hashlib,io,json,math,threading,time,uuid
from urllib.parse import quote
from PIL import Image

IDLE={'READY','RELEASED','SEGREGATED','REMOVED'}
HOLDS={'REVIEW_HOLD','GOOD_HOLD','DEFECT_HOLD','CONFLICT_HOLD'}
POLICY='FPGA_NO_ALARM_AUTO_PASS_V207'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Conveyor:
    START_X=-460;CAPTURE_X=80;REVIEW_X=780;EXIT_X=1320
    def __init__(self,api,catalog,store,incoming=4,outgoing=3):
        self.api,self.catalog,self.store=api,catalog,Path(store)
        self.store.mkdir(parents=True,exist_ok=False)
        self.lock=threading.RLock();self.run=uuid.uuid4().hex
        self.phase='IDLE';self.since=time.monotonic();self.zone_seconds=4.
        self.enabled=False;self.token=None;self.row=None;self.cycle_id=None
        self.station=api.state();self.station_session=self.station['session']
        self.queue=[];self.index=0;self.error=None;self.history=[];self.capture_meta=None
        self.review_ack=False;self.operator='';self.motion_t0=None
        self.pass_allowed=False;self.release_at=None;self.capture_at=None
        self.result_at=None;self.slow_wait_logged=False
        if self.station['phase'] in HOLDS:
            self.cycle_id=self.station['cycle']['id'];self.phase='REVIEW'
        elif self.station['phase'] not in IDLE:
            self.phase='FAULT';self.error='原工作站有未完成任务'
        self.event('session_started',adopted_cycle=self.cycle_id)

    @property
    def velocity(self):return (self.REVIEW_X-self.CAPTURE_X)/self.zone_seconds

    def position(self,now=None):
        now=now or time.monotonic()
        if self.release_at is not None:return self.REVIEW_X+(now-self.release_at)*self.velocity
        if self.motion_t0 is None:return float(self.REVIEW_X)
        x=self.START_X+(now-self.motion_t0)*self.velocity
        return x if self.pass_allowed else min(self.REVIEW_X,x)

    def permit_pass(self):
        now=time.monotonic()
        arrival=self.motion_t0+(self.REVIEW_X-self.START_X)/self.velocity if self.motion_t0 else 0
        if now>arrival:self.release_at=now
        self.pass_allowed=True

    def event(self,event,**fields):
        row=dict(utc=utc(),run=self.run,event=event,phase=self.phase,token=self.token,
                 cycle_id=self.cycle_id,x=self.position(),**fields)
        with (self.store/'events.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')

    def transition(self,phase):self.phase,self.since=phase,time.monotonic()
    def fail(self,message):
        self.enabled=False;self.error=str(message);self.transition('FAULT')
        self.event('flow_stopped',error=self.error)

    def snapshot(self):
        with self.lock:
            s=self.station;c=s.get('cycle');now=time.monotonic();x=self.position(now)
            waiting=x>=self.REVIEW_X and not self.pass_allowed and self.phase not in ['IDLE','MOVING']
            moving=self.phase not in ['IDLE','REVIEW','FAULT'] and not waiting
            return json.loads(json.dumps(dict(ui_version=207,run=self.run,phase=self.phase,
                elapsed=now-self.since,zone_seconds=self.zone_seconds,incoming=self.zone_seconds,
                outgoing=540/self.velocity,enabled=self.enabled,token=self.token,
                row={k:v for k,v in self.row.items() if k!='file'} if self.row else None,
                cycle=c if c and c['id']==self.cycle_id else None,
                station_phase=s['phase'],station_session=s['session'],
                calibrated=s.get('closed_loop',{}).get('calibrated',False),connection=s.get('connection'),
                queue=self.queue,index=self.index,samples=[{k:r[k] for k in ['id','name','sha256']} for r in self.catalog.values()],
                capture=self.capture_meta,history=self.history[-8:],error=self.error,
                review_ack=self.review_ack,operator=self.operator,
                motion=dict(x=x,velocity=self.velocity,moving=moving,
                    maximum=self.EXIT_X if self.pass_allowed else self.REVIEW_X,
                    waiting_for_result=waiting and self.phase in ['CAPTURE','SUBMITTING','INSPECTING','AUTO_CONFIRM']),
                policy_id=POLICY)))

    def _begin(self):
        if self.station['phase'] not in IDLE:raise ValueError('当前工件尚未完成处置')
        if not self.station.get('closed_loop',{}).get('calibrated'):raise ValueError('请先完成本批核验')
        if not self.station.get('automatic_pass_policy',{}).get('enabled'):raise ValueError('请先启动支持自动通过策略的工作站')
        self.row=self.catalog[self.queue[self.index%len(self.queue)]]
        if sha(Path(self.row['file']).read_bytes())!=self.row['sha256']:raise ValueError('照片源文件校验失败')
        self.token=uuid.uuid4().hex;self.cycle_id=None;self.capture_meta=None
        self.pass_allowed=False;self.release_at=None;self.motion_t0=time.monotonic()
        self.capture_at=None;self.result_at=None;self.slow_wait_logged=False
        self.transition('MOVING');self.event('tile_entered',sample_id=self.row['id'],source_sha256=self.row['sha256'])

    def action(self,body):
        with self.lock:
            if body.get('run')!=self.run:raise ValueError('流水线会话已变化，请刷新')
            op=body.get('op')
            if op=='start':
                if self.phase not in ['IDLE','REVIEW']:raise ValueError('请先完成当前工件')
                queue=body.get('queue',[])
                if not queue or len(queue)>100 or any(i not in self.catalog for i in queue):raise ValueError('请选择有效的照片队列')
                seconds=float(body.get('zone_seconds',4))
                if not math.isfinite(seconds) or not 3<=seconds<=15:raise ValueError('检测区时间请选择3至15秒')
                self.zone_seconds=seconds;self.queue=queue;self.index=-1 if self.phase=='REVIEW' else 0;self.enabled=True
                self.event('automatic_policy_authorized',policy_id=POLICY,zone_seconds=seconds,queue=queue)
                # A no-alarm tile retained from the former manual policy may pass now.
                c=self.station.get('cycle') or {}
                if self.phase=='REVIEW' and c.get('result',{}).get('pl_image_alarm')==0 and not c.get('review'):
                    self.station=self.api.action('automatic_release',policy_id=POLICY,result_id=c['result']['id'])
                    self.transition('AUTO_CONFIRM')
                elif self.phase=='IDLE':self._begin()
            elif op=='pause':self.enabled=False;self.event('pause_after_current')
            elif op=='review':self._review(body)
            elif op=='ack_review':
                if body.get('confirmed') is not True:raise ValueError('请先确认复核方式')
                self.review_ack=True;self.event('review_method_acknowledged_once')
            else:raise ValueError('未知操作')
            return self.snapshot()

    def _review(self,body):
        if self.phase!='REVIEW' or not self.cycle_id:raise ValueError('当前没有待复核工件')
        s=self.api.state();c=s.get('cycle') or {}
        if c.get('id')!=self.cycle_id or not c.get('result'):raise ValueError('工件已变化，禁止复核旧结果')
        if body.get('result_id')!=c['result']['id']:raise ValueError('复核结果已过期')
        if not self.review_ack and body.get('confirmed') is not True:raise ValueError('首次复核请确认已了解复核方式')
        operator=str(body.get('operator',self.operator)).strip()
        if not operator or len(operator)>60:raise ValueError('请填写复核员或演示代号')
        if not c.get('review'):
            s=self.api.action('review',result_id=c['result']['id'],operator=operator,
                              verdict=body.get('verdict'),note=body.get('note',''))
        self.review_ack=True;self.operator=operator
        op='release' if s['phase']=='GOOD_HOLD' else 'segregate'
        self.station=self.api.action(op,result_id=c['result']['id'],operator=operator,operator_confirmed=True)
        self.transition('CONFIRMING');self.event('human_review_recorded',operator=operator,verdict=body.get('verdict'))

    def capture(self,token,raw):
        with self.lock:
            if token!=self.token:raise ValueError('过期截帧已拒绝')
            if self.phase!='CAPTURE':
                if self.phase in ['SUBMITTING','INSPECTING','AUTO_CONFIRM','DEFECT_APPROACH','REVIEW','PASSING']:return self.snapshot()
                raise ValueError('当前不允许截帧')
            with Image.open(io.BytesIO(raw)) as image:
                if image.format!='PNG':raise ValueError('只接收PNG帧')
                with Image.open(self.row['file']) as original:
                    image=image.convert('RGB');original=original.convert('RGB')
                    if image.size!=original.size or image.tobytes()!=original.tobytes():raise ValueError('截帧与本次入线照片像素不一致')
                    rgb_sha=sha(image.tobytes())
            (self.store/(token+'.png')).write_bytes(raw);self.capture_at=time.monotonic()
            self.capture_meta=dict(frame_sha256=sha(raw),rgb_sha256=rgb_sha,source_sha256=self.row['sha256'],
                capture_utc=utc(),method='moving_browser_canvas_native_tile_ROI',camera=False,hdmi_capture=False)
            self.transition('SUBMITTING');self.event('moving_frame_captured',**self.capture_meta)
            threading.Thread(target=self._submit,args=(token,raw),daemon=True).start()
            return self.snapshot()

    def _submit(self,token,raw):
        try:
            with self.lock:
                if token!=self.token:raise ValueError('截帧任务已过期')
                upload=json.loads(self.api.request('/api/upload',raw,{'Content-Type':'image/png','X-File-Name':quote('移动截帧_'+token+'.png')}))
                s=self.api.action('load',sample_id=upload['sample_id'],purpose='inspection',conditions_confirmed=True)
                self.cycle_id=s['cycle']['id'];self.station=s
                self.event('frame_bound_to_cycle',frame_sha256=sha(raw))
                self.station=self.api.action('inspect',input_held_confirmed=True)
                self.transition('INSPECTING')
        except Exception as error:
            with self.lock:self.fail(error)

    def _record(self,c):
        self.history.append(dict(cycle_id=c['id'],result_id=c['result']['id'],alarm=c['result']['pl_image_alarm'],
            review=c.get('review'),disposition=c['disposition'],automatic=c['disposition']['command']=='automatic_pass'))

    def tick(self):
        with self.lock:
            s=self.api.state();self.station=s
            if s['session']!=self.station_session:
                if self.phase!='FAULT':self.fail('原工作站已重启，请重新建立流水线会话')
                return
            if s['phase']=='FAULT':
                if self.phase!='FAULT':self.fail(s.get('error') or 'FPGA工作站故障')
                return
            c=s.get('cycle') or {}
            if self.cycle_id and c.get('id')!=self.cycle_id:
                if self.phase!='FAULT':self.fail('其他页面切换了工件，旧标记已作废')
                return
            x=self.position();elapsed=time.monotonic()-self.since
            if self.phase=='MOVING' and x>=self.CAPTURE_X:
                self.transition('CAPTURE');self.event('capture_zone_entered_without_stop')
            elif self.phase=='CAPTURE' and elapsed>20:self.fail('显示页面未完成截帧')
            elif self.phase=='INSPECTING':
                if s['phase'] in HOLDS:
                    r=c.get('result') or {}
                    if c.get('source_sha256')!=self.capture_meta['frame_sha256'] or r.get('input_file_sha256')!=self.capture_meta['frame_sha256']:
                        self.fail('FPGA结果与本次截帧不匹配');return
                    self.result_at=time.monotonic()
                    self.capture_meta['capture_to_result_seconds']=self.result_at-self.capture_at
                    self.event('fpga_result_received_while_moving',result_id=r['id'],frame_sequence=r['pl_frame_sequence'],
                        alarm=r['pl_image_alarm'],capture_to_result_seconds=self.result_at-self.capture_at)
                    if r['pl_image_alarm']==0:
                        self.station=self.api.action('automatic_release',policy_id=POLICY,result_id=r['id'])
                        self.transition('AUTO_CONFIRM')
                    else:self.transition('DEFECT_APPROACH' if x<self.REVIEW_X else 'REVIEW')
                elif elapsed>40:self.fail('等待FPGA结果超时，工件在复核区保持停止')
            elif self.phase=='AUTO_CONFIRM' and s['phase']=='RELEASED':
                self._record(c);self.permit_pass();self.transition('PASSING')
                self.event('no_alarm_pass_without_human_review',no_human_review=True)
            elif self.phase=='DEFECT_APPROACH' and x>=self.REVIEW_X:
                self.transition('REVIEW');self.event('alarmed_tile_stopped_at_review')
            elif self.phase=='CONFIRMING':
                if s['phase'] in IDLE:
                    self._record(c);self.permit_pass();self.transition('OUTGOING')
                    self.event('tile_leaving_after_human_review',disposition=c['disposition'])
                elif elapsed>30:self.fail('处置校验超时')
            if self.phase in ['PASSING','OUTGOING'] and self.position()>=self.EXIT_X:
                self.index+=1
                if self.enabled:self._begin()
                else:
                    self.transition('IDLE');self.cycle_id=None;self.row=None;self.token=None;self.motion_t0=None
            if self.phase in ['CAPTURE','SUBMITTING','INSPECTING','AUTO_CONFIRM'] and self.position()>=self.REVIEW_X and not self.slow_wait_logged:
                self.slow_wait_logged=True;self.event('late_result_stop_at_review',automatic_pass_forbidden=True)
