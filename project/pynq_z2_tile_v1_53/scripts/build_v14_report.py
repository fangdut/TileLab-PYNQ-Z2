"""Report is generated only after final_summary.json is compiled from test evidence."""
from pathlib import Path
import json
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
R=Path(__file__).resolve().parents[1];T=R/'reports/v14';S=json.loads((T/'final_summary.json').read_text(encoding='utf-8'))
D=Document();sec=D.sections[0];sec.page_width=Cm(21);sec.page_height=Cm(29.7);sec.top_margin=sec.bottom_margin=Cm(1.8);sec.left_margin=sec.right_margin=Cm(2)
for name,size in [('Normal',10.5),('Title',23),('Heading 1',17),('Heading 2',12)]:
 st=D.styles[name];st.font.name='Times New Roman';st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0);st._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'宋体' if name=='Normal' else '微软雅黑')
D.styles['Normal'].paragraph_format.line_spacing=1.08;D.styles['Normal'].paragraph_format.space_after=Pt(5)
for st in D.styles:
 for e in list(st.element.iter(qn('w:pBdr'))):e.getparent().remove(e)
notes=[]
def p(t):notes.append(t);return D.add_paragraph(t)
def h(t):notes.append('\n## '+t);D.add_heading(t,2)
def page(t):
 notes.append('\n# '+t);pa=D.add_heading(t,1);pa.paragraph_format.page_break_before=True
def table(headers,rows,widths):
 t=D.add_table(rows=1,cols=len(headers));t.autofit=False
 for c,w in zip(t.columns,widths):c.width=Cm(w)
 for c,v in zip(t.rows[0].cells,headers):c.text=str(v)
 t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
 for row in rows:
  for c,v in zip(t.add_row().cells,row):c.text=str(v)
 for i,row in enumerate(t.rows):
  row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
  for j,c in enumerate(row.cells):
   c.width=Cm(widths[j]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER;pr=c._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
   for side in ('top','left','bottom','right','insideH','insideV'):
    e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');b.append(e)
   pr.append(b);sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E8EFF4' if i==0 else 'FFFFFF');pr.append(sh);mar=OxmlElement('w:tcMar')
   for side in ('top','left','bottom','right'):
    e=OxmlElement('w:'+side);e.set(qn('w:w'),'85');e.set(qn('w:type'),'dxa');mar.append(e)
   pr.append(mar)
   for pa in c.paragraphs:
    pa.paragraph_format.space_after=Pt(3);pa.paragraph_format.line_spacing=1.06
    for run in pa.runs:run.font.size=Pt(10);run.bold=i==0
 notes.append(' | '.join(headers));notes.extend(' | '.join(map(str,r)) for r in rows);p('')
def eq(t):
 notes.append(t);pa=D.add_paragraph();m=OxmlElement('m:oMath');r=OxmlElement('m:r');e=OxmlElement('m:t');e.text=t;r.append(e);m.append(r);pa._p.append(m)
def picture(path,width=16.5):
 run=D.add_paragraph().add_run();shape=run.add_picture(str(path),width=Cm(width));shape._inline.docPr.set('descr',Path(path).stem)
footer=sec.footer.paragraphs[0];footer.alignment=2;footer.add_run('Tile V1.4  ');e=OxmlElement('w:fldSimple');e.set(qn('w:instr'),'PAGE');footer._p.append(e)
D.add_paragraph('瓷砖连续检测与最佳截图验证报告','Title')
p('PYNQ Z2   V1.4   2026 年 9 月 26 日')
p(S['conclusion'])
p('本项目是可复核的瓷砖缺陷候选检测原型。电脑通过 HDMI 模拟相机，FPGA 计算候选和框，ARM 管理帧缓存与以太网，电脑保存证据并人工审核。本轮按采集连续性、产品最佳截图、真实测试集的顺序改进，旧版工程完整保留。')
table(['任务','本轮结果'],S['task_rows'],[4,13])
h('必须区分的两种通过')
p('工程链路通过，指输入、检测、缓存、传输和留图的数据一致性及稳定性通过给定测试。工业识别准确率通过，需要真实相机、光照、材质、线速和独立标注样本。本轮真实纹理瓷砖评估暴露了明显误报，不能把工程测试结果等同于工厂可用。')
h('旧项目与证据保留')
p('旧项目 D:\\Vivado\\pynq_z2_tile_v1_3 保持可用。本版为 D:\\Vivado\\pynq_z2_tile_v1_5，Vitis 工作区就是同名 .sdk 文件夹。原 500 条历史记录复制保留，并实际取回旧板积压的 12 条。没有通过删除旧证据解除阻塞。')

page('连续采集架构与硬件优化')
h('为什么以前可能漏采')
p('旧程序按帧启动简单 DMA。DMA 是直接内存访问硬件，它把像素搬到 DDR 内存，不需要 CPU 逐像素复制。旧程序处理网络或维护任务时，下一帧可能已经到达而 DMA 尚未重新启动，这会产生采集间隙。FPGA 仍在检测，不代表每张图都已经完整保存进内存。')
h('现在如何连续接收')
p('新版采用 SG DMA。SG 是分散聚集的缩写，可理解为预先排好的搬运任务表。32 个描述符提前写好地址和长度；DMA 自动接收下一帧，ARM 只处理已完成的任务并补回空闲缓冲区。每张图后附 40 个 32 位元数据字，图像与坐标在同一数据包内结束，避免读取到下一帧的寄存器快照。')
eq('帧像素数据 = 1280 × 720 × 4 = 3,686,400 字节')
eq('DMA 包长 = 3,686,400 + 40 × 4 = 3,686,560 字节')
p('每个像素依次保存蓝、绿、红、候选掩码，各占一个字节。AXI Stream 的 TLAST 表示本包结束，放在元数据最后，而不是最后一个像素。若 FIFO 无法及时接收像素，会明确标记无效包，ARM 不将其作为证据。')
h('缓冲区不会互相覆盖的条件')
p('DDR 划分为 48 个 4 MiB 槽。32 个用于 DMA 预排任务，最多 12 个保存尚未确认的事件，还有一个最佳帧可能被保留。相同帧同时作为预览和产品证据时采用引用计数；只有全部确认后才能重用。电脑必须先完整落盘再发送应用确认。断线只撤销 TCP 传输，不释放未确认事件。')
h('实际修复的时序问题')
p('首轮实现最差时序裕量为 −0.383 ns，路径位于区域搜索队列。原 RTL 用两个不同地址的写入分支加一个读取端口，无法推导为目标双口 BRAM，队列被展开成大量寄存器。改成一个复用地址的写端口和一个同步读端口后，算法输出不变，硬件结构可使用片上 RAM。')
table(['指标','修复后'],S['hardware_rows'],[6,11])
p('像素时钟仍是 74.25 MHz，HP0 与 DMA 为 100 MHz，HDMI 接收参考时钟为 200 MHz。本轮没有靠提高像素时钟解决问题；先消除调度空隙和低效存储结构。')

page('按瓷砖编号选择最佳证据')
h('产品编号从哪里来')
p('FPGA 在画面中心列统计亮表面像素，超过门限表示瓷砖进入检测中心；连续两帧没有满足条件则结束当前产品。编号由 FPGA 递增，电脑不根据视频文件名猜测编号。启动编号区分不同烧录会话，同一块板重新下载后也不会覆盖旧产品证据。')
h('最佳截图不是第一张报警图')
p('在当前产品经过期间，FPGA 持续比较有效报警帧。先选择亮表面左右边缘都完整进入检测范围的帧，再选候选面积较大的帧；面积相同则选更居中的帧。ARM 根据 FPGA 的更新标志保留对应 DDR 槽，产品结束时才把最佳帧放入待传队列。')
eq('排序优先级 = 完整入镜标志 → 候选面积 → 更小的中心距离')
eq('中心距离 = | x最左 + x最右 − 1279 |')
p('“完整”是基于亮表面边界的工程判据，不是语义分割保证。暗色瓷砖、反光、遮挡和复杂背景可能使它失效。保存的文件名为 tile_启动编号_产品编号.png，掩码另存为 _mask.png，并保留原图，不把红框永久画进证据。页面按同帧坐标叠加红框。')
if S.get('best_example'):
 picture(R/S['best_example'],12.5);p('图 1  本版实板回传并保存的完整产品证据。图像来源和框数据均经过 FPGA 链路。')
h('现在的适用范围')
p('当前适用于暗背景、亮瓷砖、单通道及明确产品间隔，检测中心同时只处理一个产品。匀速视频使用固定间距满足这个条件，没有等待采集的停车动作。多块瓷砖缺陷同时进入视野或产品相接时，仍需光电触发、编码器或 FPGA 产品区域关联。静态瓷砖不会自行离站，可切换空带或使用手动留图。')
h('长视频输入的补充验证')
p(S['long_stream_detail'])
p(S['player_fix_detail'])

page('实板测试与速度边界')
p('环境为 PYNQ-Z2、电脑 HDMI 输入、显示器 HDMI 输出、USB JTAG 下载及 1 Gbps 直连网线。下面统计基于本版实测日志，完整取帧、PNG 编码和数据库保存分别计时。测试速度单位是像素/秒，尚未标定为真实传送带米/秒。')
table(['测试','采集帧率','最长取图间隔','新增间隙 无效 丢失'],S['continuous_rows'],[4.2,3,4.1,5.7])
p(S['test_detail'])
h('完整性和异常测试')
for t in S['validation_paragraphs']:p(t)
h('千兆网为什么不能传所有原始帧')
eq('原始帧带宽 = 3,686,400 × 60 = 221.184 MB/s')
eq('千兆网理论上限 = 1,000,000,000 ÷ 8 = 125 MB/s')
p('因此可以让 FPGA 每帧检测并连续写入 DDR，但不能用当前无压缩格式把全部 60 帧/秒传给电脑。电脑接收抽样预览和保留的最佳事件；检测帧率、DMA 采集帧率、电脑取帧率和浏览器刷新率不能混为一谈。')
p('网络增加了收发描述符和诊断，发送端按约 50 微秒一批、每批最多 2920 字节进行非阻塞限速，接收端预留 8 MiB 缓冲。常态下 350 毫秒无新字节则重连，最多重试一次；新连接首图允许 2 秒无数据等待，避免冷启动恢复被过早打断。首图可能比表中稳定窗口耗时长，但 FPGA 继续采集。初版曾停顿约 2.3 秒，发送节奏调整后重新验收。')
p('新结果仅证明本次窗口内的表现，不等同于无限时长或断电不丢图。板端队列在 DDR 中，掉电会丢失尚未传出的记录。')

page('真实瓷砖数据与识别能力评估')
p('数据采用 MVTec AD 的 tile 类别，来自公开镜像并保留原始来源、训练测试划分、标签、像素标注和 SHA256。照片共 347 张，其中训练正常 230 张，测试正常 33 张，测试缺陷 84 张。测试缺陷包括裂纹 17 张、胶带 18 张、灰色划痕 16 张、油污 18 张和粗糙缺陷 15 张。')
p('本轮先固定原有阈值 36 和半径 8，不用测试集挑选更漂亮的参数。840×840 照片等比例缩到 500×500，放入 720p 场景。缺陷掩码采用最近邻缩放，原照片保留。平移照片得到的是合成运动场景，不能替代真实相机的曝光、运动模糊和光照验证。')
table(['裂纹与正常照片','报警','不报警'],[['裂纹 17 张','17','0'],['正常 33 张','33','0']],[7,5,5])
p('裂纹召回率为 100%，但正常样本误报率也为 100%。单独宣传召回率没有意义：当前算法无法区分这种花纹和裂纹。两类合计 50 张样本的报警精确率仅 34%，且受测试集类别比例影响。其余缺陷单独统计，不把它们当作正常样本。')
picture(T/'real_dataset/examples.png',15.5)
p('图 2  离线参考输出示例。左上为正常纹理瓷砖，同样产生大范围误报；其余为缺陷样本。完整统计见 real_dataset/metrics.json，不能将这些离线结果标作实板准确率。')
p(S['real_board_detail'])
p('来源：MVTec AD 官方数据页 https://www.mvtec.com/research-teaching/datasets/mvtec-ad 。下载镜像为 Voxel51/mvtec-ad。许可为 CC BY-NC-SA 4.0，要求署名、非商业使用和相同方式共享；实际商业部署需要另行取得合适数据授权。')

page('操作步骤与故障定位')
h('接线与启动')
for t in [
 '1  电脑 HDMI 输出接开发板 HDMI IN，开发板 HDMI OUT 接显示器。Windows 设置扩展屏，选择 1280×720、60 Hz。板子不带相机，本轮由电脑输出测试图像。',
 '2  USB 数据线连接板上 PROG UART 与电脑，用于 JTAG 下载和串口。普通网线连接板子 RJ45 与电脑网口，用于传图。USB 串口和网口承担不同任务，不能相互代替。',
 '3  打开本版 .sdk 文件夹，运行 program_ethernet.bat。默认板地址为 169.254.200.10，电脑网口应在 169.254/16 网段。下载只更新易失性 FPGA 配置和 ARM 内存，不写 Flash 或 SD。',
 '4  运行工程根目录的启动以太网工作站.bat，打开 http://127.0.0.1:8770 。选择匀速流水线并点击开始采集，等待产品通过检测中心后在复核列表查看最佳图。',
 '5  点击记录查看原图、同帧红框和掩码，标记确认裂纹、误报或需复查。CSV 和 JSON 均可导出产品编号与复核信息。分页只影响浏览，不限制后台留图。',
 '6  暂停只停止电脑取图，FPGA 仍然工作。板端待确认事件达到 12 张后会明确计数丢失；长时间暂停前宜把输入切换为空带。磁盘保护触发时先释放空间，再恢复接收。']:p(t)
h('从症状定位问题')
table(['现象','先检查'],[['无信号','HDMI 方向、扩展屏 720p60、显示器输入和下载是否成功'],['页面长期无数据','固件与工程版本、网口地址、TCP 9133 和页面错误'],['静态裂纹未自动存图','产品尚未离开中心门；切空带或手动留图'],['队列满丢失计数增加','电脑暂停、网络慢或事件频率超过排空能力'],['正常纹理也报警','算法误报，不能靠加快网口或提高时钟解决'],['高速 HDMI 框有偏移','HDMI 直通叠框仍使用上一帧坐标；PC 存图使用同帧坐标']],[5,12])
h('复现位置')
p('硬件创建与重建：scripts/create_project.tcl 和 scripts/rebuild.tcl。Vitis 构建：.sdk/build_ethernet.py。仿真：test_capture_sg.tcl 和 test_regions_bram.tcl。实板测试：board_v14_continuous.py、board_v14_queue.py 和静态验收脚本。原始日志与统计在 reports/v14，软件和硬件内容哈希见交付清单。')

page('答辩原理与下一步计划')
h('需要能自己讲清的原理')
p('流水线指每级寄存器只做一部分工作。它可能需要多拍才输出第一个结果，但稳定后可以每拍接收一个像素。这与等待整张图片处理完再处理下一张不同。BRAM 是 FPGA 自带的存储块；DDR 是板外大容量内存；FIFO 是先入先出的缓冲；CDC 是跨时钟域传递，需要同步与握手，不能把多位数据逐位随意连接。')
eq('灰度 Y = (77R + 150G + 29B) / 256 取整')
p('暗谷检测沿水平、垂直和两条对角线比较像素两侧。若中心比两侧都暗，就可能是裂纹。取四个方向中最大的暗谷分数，大于阈值 36 即成为候选。表面花纹也可能满足条件，所以它是候选提取器，不是训练好的语义模型，也不是 YOLO。')
eq('方向分数 = min(正方向邻点灰度, 反方向邻点灰度) − 中心灰度')
p('区域模块把候选落入每格 32×32 像素的网格，再按八邻域连接。八邻域表示上下左右和四个斜方向都算相邻。每格保留候选数量和精确极值，最终最多输出八个框；附近独立缺陷可能因网格而合并。至少 32 个候选像素且长边跨度至少 23 像素才形成保留区域。')
h('建议优先级')
table(['次序','改进方向','验收方法'],[['1','用训练正常纹理统计和方向连续性抑制花纹；再定点化到 FPGA','固定独立留出集，分别报告漏检、误报和像素定位'],['2','加入光电触发或编码器与每个产品的区域关联','相接产品、变速、多产品同视野，核对编号和框的归属'],['3','增加同帧 DDR 回放叠框及低带宽预览通道','高速运动时 HDMI 与 PC 框均对齐，证据原图不降质'],['4','长时运行、网络中断、磁盘满及掉电恢复','连续数小时和故障注入；记录所有丢失和恢复时间']],[1.4,8,7.6])
p('优先修复识别可信度，而不是继续叠加演示功能。再提高频率只能增加吞吐余量，不能解决花纹误报、光学模糊或产品编号混淆。实际线速还受曝光限制：运动模糊约等于图像移动速度乘曝光时间，需要相机、镜头和照明共同设计。')
p('建议学习顺序：Verilog 时序逻辑与仿真 → 视频行场同步和消隐 → AXI Stream 握手 → BRAM 与 DMA 描述符 → TCP 与应用确认 → 灰度、局部对比、连通区域和分类评价。结合本版代码和对应测试逐段解释，先能复现一个静态样本，再说明连续产品为什么不会覆盖正在传输的图。')
out=R/'docs/Tile_V1.4_连续采集最佳截图与真实数据评估报告.docx';out.parent.mkdir(exist_ok=True);D.save(out)
(out.with_suffix('.md')).write_text('\n\n'.join(notes),encoding='utf-8');print(out)
