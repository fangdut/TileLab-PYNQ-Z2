"""Bounded local player adoption telemetry, independent of HDMI reception."""
from pathlib import Path
from datetime import datetime
import json,os,time
from render_progress import RenderProgress
from stimulus_command import valid_source,valid_id,parse_command,MAX_COMMAND_BYTES

def read_small(path,limit):
    with path.open('rb') as f:
        raw=f.read(limit+1);modified=os.fstat(f.fileno()).st_mtime
    if len(raw)>limit:raise ValueError('状态文件过大')
    return raw.decode('utf-8-sig').strip(),modified

def timestamp(value):
    stamp=datetime.fromisoformat(value)
    if stamp.tzinfo is None:raise ValueError('时间缺少时区')
    return stamp.timestamp()

class StimulusStatus:
    freshness_seconds=1.5
    def __init__(self,root):
        self.directory=Path(root)/'host';self.last_requested=None;self.last_request_id=None;self.render_progress=RenderProgress()
    def requested(self,value,request_id=None):
        if not valid_source(value) or (request_id is not None and not valid_id(request_id)):raise ValueError('Unknown stimulus or request ID')
        self.last_requested=value;self.last_request_id=request_id
    def snapshot(self,now=None,monotonic_now=None):
        now=time.time() if now is None else now
        monotonic_now=time.monotonic() if monotonic_now is None else monotonic_now
        result=dict(requested=self.last_requested,request_id=self.last_request_id,observed=None,observed_request_id=None,
            player_session=None,active_player_session=None,player_pid=None,command_protocol=None,identity_confirmed=False,
            motion=dict(state='UNCONFIRMED',progressing=None,message='输入身份未确认，暂不判断绘制进展'),phase=None,age_seconds=None,ready=False,state='COMMAND_UNAVAILABLE',message='',command_error='',player_error='',
            rendered_frames=None,source_frame=None,scope='LOCAL_PLAYER_ADOPTION_NOT_HDMI_LINK')
        def fail(state,message,**fields):
            result.update(state=state,message=message,**fields);return result
        try:
            command_raw,modified=read_small(self.directory/'display_command.txt',MAX_COMMAND_BYTES)
            command=parse_command(command_raw);self.requested(command['source'],command['request_id'])
            result.update(requested=self.last_requested,request_id=self.last_request_id,command_protocol=command['version'])
        except (OSError,UnicodeError,ValueError) as e:
            return fail('COMMAND_UNAVAILABLE','输入命令暂不可读；保留上次请求，板端采集独立继续',command_error=str(e))
        try:
            raw,_=read_small(self.directory/'player_status.json',16384);p=json.loads(raw)
            if not isinstance(p,dict) or not valid_source(p.get('source')):raise ValueError('播放器输入标识无效')
            if p.get('phase') not in ('static','rendering','loading','priming','playing'):raise ValueError('播放器阶段无效')
            emitted=timestamp(p['utc']);age=now-emitted
            for key in ('rendered_frames','source_frame'):
                if type(p.get(key)) is not int or p[key]<0:raise ValueError('播放器帧计数无效')
            if p.get('error') is not None and not isinstance(p['error'],str):raise ValueError('播放器错误字段无效')
            result.update(observed=p['source'],phase=p['phase'],age_seconds=round(age,3),rendered_frames=p['rendered_frames'],source_frame=p['source_frame'])
        except OSError as e:return fail('PLAYER_UNAVAILABLE','播放器状态暂不可读；尚不能确认输入',player_error=str(e))
        except (UnicodeError,ValueError,KeyError,TypeError,OverflowError) as e:return fail('PLAYER_INVALID','播放器状态格式无效；尚不能确认输入',player_error=str(e))
        if age<-.5 or modified>now+.5:return fail('CLOCK_UNCERTAIN','播放器或命令时间位于未来；暂不确认输入')
        if age>self.freshness_seconds:return fail('STALE','播放器状态已过期；不能确认当前输入')
        if p.get('error'):return fail('PLAYER_ERROR','播放器报告错误；输入未确认',player_error=p['error'])
        if p['source']!=command['source'] or emitted<modified or p['phase'] in ('loading','priming'):
            return fail('SWITCHING','切换请求已保存，等待播放器报告对应输入')
        if command['version']==0:return fail('LEGACY_UNCONFIRMED','旧式命令没有请求编号，不能确认此次请求；请重新选择输入')
        if not valid_id(p.get('request_id')) or not valid_id(p.get('player_session')) or type(p.get('player_pid')) is not int or p['player_pid']<=0:
            return fail('PLAYER_IDENTITY_MISSING','播放器没有有效的请求编号或启动身份；输入未确认')
        result.update(observed_request_id=p['request_id'],player_session=p['player_session'],player_pid=p['player_pid'])
        try:
            marker_raw,_=read_small(self.directory/'player_instance.json',512);marker=json.loads(marker_raw)
            if not isinstance(marker,dict) or type(marker.get('version')) is not int or marker['version']!=1 or not valid_id(marker.get('session')) or type(marker.get('pid')) is not int or marker['pid']<=0:raise ValueError('启动身份格式无效')
            started=timestamp(marker['started_utc']);result['active_player_session']=marker['session']
            again,_=read_small(self.directory/'player_instance.json',512)
            if again!=marker_raw:return fail('PLAYER_SESSION_SWITCHING','读取期间播放器启动身份发生变化；等待下一次报告')
        except OSError as e:return fail('PLAYER_INSTANCE_UNAVAILABLE','播放器启动身份暂不可读；尚不能确认输入',player_error=str(e))
        except (UnicodeError,ValueError,KeyError,TypeError,OverflowError) as e:return fail('PLAYER_INSTANCE_INVALID','播放器启动身份无效；尚不能确认输入',player_error=str(e))
        if started>now+.5:return fail('CLOCK_UNCERTAIN','播放器启动时间位于未来；暂不确认输入')
        if p['player_session']!=marker['session'] or p['player_pid']!=marker['pid'] or emitted<started:
            return fail('PLAYER_SESSION_SWITCHING','等待当前播放器的报告；旧进程报告不能确认新输入')
        if p['request_id']!=command['request_id']:return fail('SWITCHING','名称已相同，但当前请求编号尚未被播放器采用')
        try:
            again,_=read_small(self.directory/'display_command.txt',MAX_COMMAND_BYTES)
            if again!=command_raw:return fail('SWITCHING','读取期间输入请求已更新；等待新请求的确认')
        except (OSError,UnicodeError,ValueError) as e:return fail('COMMAND_UNAVAILABLE','确认期间输入命令暂不可读；板端采集独立继续',command_error=str(e))
        result['motion']=self.render_progress.observe(p,monotonic_now)
        return fail('READY','当前播放器已回报此请求编号；仅确认软件采用，HDMI 采集请看板端健康状态',ready=True,identity_confirmed=True)
