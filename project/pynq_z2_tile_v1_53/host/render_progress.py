"""Observe local WPF drawing progress; never claim to observe HDMI scanout."""
import math

class RenderProgress:
    stall_seconds=1.0
    observation_gap_seconds=1.5
    periods={'video':720,'real_video':720,'dark_video':720,'fast':360,'ultrafast':180}
    def __init__(self):self.key=None
    def _baseline(self,key,count,source,now):
        self.key=key;self.count=count;self.source=source;self.last_seen=now;self.last_progress=now;self.seen_progress=False
    def observe(self,p,now):
        result=dict(state='UNOBSERVED',progressing=None,drawn_frames=p.get('drawn_frames'),drawn_source_frame=p.get('drawn_source_frame'),
            no_progress_seconds=None,message='',scope='LOCAL_WPF_DRAWING_NOT_HDMI_SCANOUT')
        def out(state,message,progressing=None,**extra):
            result.update(state=state,message=message,progressing=progressing,**extra);return result
        if p['phase']=='static':
            self.key=None;return out('NOT_REQUIRED','当前是静态图片，无需检查画面运动')
        if p['phase']!='rendering' or p['source'] not in self.periods:
            self.key=None;return out('UNOBSERVED','此媒体源尚无逐帧绘制监测；不能仅凭播放状态确认画面运动')
        count=p.get('drawn_frames');source=p.get('drawn_source_frame')
        if type(count) is not int or count<0 or type(source) is not int or not 0<=source<self.periods[p['source']]:
            return out('INVALID','运动源缺少有效绘制计数；不能确认画面进展')
        if not isinstance(now,(int,float)) or not math.isfinite(now):
            self.key=None;return out('CLOCK_UNCERTAIN','本机进度计时无效；等待重新观察')
        key=(p['player_session'],p['source'])
        if key!=self.key:
            self._baseline(key,count,source,now);return out('WAITING','已采用运动源，等待观察新的绘制帧',False,no_progress_seconds=0)
        if now<self.last_seen or now-self.last_seen>self.observation_gap_seconds:
            self._baseline(key,count,source,now);return out('WAITING','观察曾中断，正在重新确认绘制进展',False,no_progress_seconds=0)
        if count<self.count:
            self._baseline(key,count,source,now);return out('COUNTER_RESET','绘制计数已复位；等待新的连续帧',False,no_progress_seconds=0)
        if count>self.count and source!=self.source:
            self.last_progress=now;self.seen_progress=True
        self.count=count;self.source=source;self.last_seen=now;age=now-self.last_progress
        if age>self.stall_seconds:return out('STALLED','状态仍在更新，但超过 1 秒未观察到运动源绘制进展',False,no_progress_seconds=round(age,3))
        if not self.seen_progress:return out('WAITING','等待下一张不同的绘制帧',False,no_progress_seconds=round(age,3))
        return out('PROGRESSING','本机运动源绘制持续前进；物理输出以板端图像为准',True,no_progress_seconds=round(age,3))
