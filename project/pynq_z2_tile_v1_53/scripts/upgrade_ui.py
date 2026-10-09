from pathlib import Path
r=Path(__file__).resolve().parents[1];p=r/'host/workstation.html';s=p.read_text(encoding='utf-8')
s=s.replace('<div id="workView">','<div class="panel" style="margin-bottom:18px"><div class="info-strip" style="flex-wrap:wrap"><span>板端待取<b id="queueDepth">— / 12</b></span><span>板端事件<b id="eventTotal">—</b></span><span>队列满丢失<b id="queueDropped">—</b></span><span>无效采集<b id="invalidFrames">—</b></span><span>本帧区域<b id="regionCount">— / 8</b></span></div><div id="queueWarning" style="padding:12px 18px;display:none;color:#b43e39;background:#fff0e9" role="alert"></div></div><div id="workView">')
s=s.replace('</select><div class="', '</select><div class="',1)
tag='<option value="video">'
pos=s.find(tag)
if pos>=0:s=s[:pos]+'<option value="station_4">两个分离裂纹</option><option value="station_5">孤立小点干扰</option><option value="burst">短事件压力测试</option>'+s[pos:]
s=s.replace("function render(){const s=state,rs=s.records||[];", "function render(){const s=state,rs=s.records||[];const q=s.frame||{};$('queueDepth').textContent=(q.queue_depth??'—')+' / 12';$('eventTotal').textContent=q.event_total??'—';$('queueDropped').textContent=q.events_dropped??'—';$('invalidFrames').textContent=q.invalid_frames??'—';$('regionCount').textContent=(q.boxes?.length??'—')+' / 8';const warning=(q.events_dropped?'板端队列曾满，有 '+q.events_dropped+' 个事件未能留存。请加快传输或降低事件频率。 ':'')+(q.region_overflow?'当前帧超过 8 个合格区域，未显示全部框。':'');$('queueWarning').textContent=warning;$('queueWarning').style.display=warning?'block':'none';")
s=s.replace('点击「开始采集」读取开发板帧缓存','点击「开始采集」接收板端事件和抽样预览')
s=s.replace('已暂停','接收已暂停')
s=s.replace('HDMI IN → FPGA → DDR → PC','HDMI → FPGA 多区域检测 → 事件队列 → 复核')
s=s.replace("c.fillText('候选裂痕',x+4,ly+18)","c.fillText('候选裂痕 '+(boxes.indexOf(b)+1),x+4,ly+18)")
s=s.replace('112,25','128,25')
s=s.replace('USB JTAG 调试传输','USB JTAG · 板端事件缓存')
p.write_text(s,encoding='utf-8')
