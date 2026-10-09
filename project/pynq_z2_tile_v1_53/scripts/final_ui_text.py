from pathlib import Path
r=Path(__file__).resolve().parents[1];p=r/'host/workstation.html';s=p.read_text(encoding='utf-8')
s=s.replace('候选报警首次出现时自动留图。连续报警归为同一事件；出现无报警采样帧后重新允许留图。','板端在报警开始时留图，连续 3 张有效采集帧无报警后重新触发。暂停只停止电脑接收，板端仍检测和缓存。')
s=s.replace('当前单个总包围框不等同于多目标检测；USB JTAG 不适合生产线连续图像回传。后续可接入以太网，保留同样的审核工作流。','最多显示 8 个 FPGA 区域框，32×32 网格会合并邻近缺陷。板端保留 12 张待确认帧，队列满时计数告警。以太网可选固件须另行接线验收。')
s=s.replace('<b>USB JTAG · 板端事件缓存</b>','<b id="transportName">USB JTAG · 板端事件缓存</b>')
s=s.replace("const q=s.frame||{};", "const q=s.frame||{};$('transportName').textContent=q.transport==='ETHERNET_TCP'?'以太网 TCP':'USB JTAG · 事件缓存';")
s=s.replace('预览为低速取样帧，FPGA 检测持续运行。','预览优先显示历史待取事件，可能落后于显示器。FPGA 检测持续运行。')
p.write_text(s,encoding='utf-8')
