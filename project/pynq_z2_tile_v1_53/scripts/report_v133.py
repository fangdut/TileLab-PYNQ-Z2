"""A four-page, evidence-backed addendum to the sealed V1.32 manual."""
from pathlib import Path
import hashlib, html, json, shutil, datetime
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle

R=Path(__file__).resolve().parents[1];O=R/'reports/v133'
S=json.loads((O/'validation_summary.json').read_text(encoding='utf-8'))
assert S['passed']
OUT=Path('C:/Users/Fang/Documents/Codex/2026-09-07/a/output/pdf');OUT.mkdir(exist_ok=True,parents=True)
pdf=OUT/'TileLab_V1.33_证据存档并发修复增补报告.pdf'
pdfmetrics.registerFont(TTFont('Song','C:/Windows/Fonts/simsun.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('Hei','C:/Windows/Fonts/simhei.ttf'))
navy=colors.HexColor('#143346');teal=colors.HexColor('#087e85');ink=colors.HexColor('#253c4a');muted=colors.HexColor('#617685');light=colors.HexColor('#edf5f5')
styles={n:ParagraphStyle(n,fontName=('Hei' if n=='h' else 'Song'),fontSize=s,leading=l,textColor=(teal if n=='h' else ink),wordWrap='CJK') for n,s,l in [('p',11,18),('h',14,22),('small',9.5,15)]}
c=canvas.Canvas(str(pdf),pagesize=(595.276,841.89));c.setTitle('TileLab V1.33 证据存档并发修复增补报告');c.setAuthor('TileLab 项目')
bottoms=[];y=0
def p(text,kind='p'):
    global y
    flow=Paragraph(html.escape(text).replace('\n','<br/>'),styles[kind]);w,h=flow.wrap(499,740)
    assert y-h>=65,('page overflow',text[:20],y,h)
    flow.drawOn(c,48,y-h);y-=h+10;bottoms.append(y)
def table(head,rows):
    global y
    data=[[Paragraph(html.escape(str(x)),styles['small']) for x in row] for row in [head]+rows]
    t=Table(data,colWidths=[135,364]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),light),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#d7e2e7'))]))
    w,h=t.wrap(499,740);assert y-h>=65,('table overflow',y,h);t.drawOn(c,48,y-h);y-=h+15;bottoms.append(y)
def page(number,title,kicker):
    global y
    if number>1:c.showPage()
    c.setFillColor(navy);c.rect(0,818,595.276,24,fill=1,stroke=0)
    c.setFont('Hei',10);c.setFillColor(teal);c.drawString(48,785,'TileLab / 工程迭代增补 · V1.33')
    c.setFont('Hei',23);c.setFillColor(navy);c.drawString(48,746,title)
    y=717;p(kicker,'small')
    c.setStrokeColor(colors.HexColor('#d7e2e7'));c.line(48,51,547,51)
    c.setFont('Song',9);c.setFillColor(muted);c.drawString(48,34,'软件验证通过 · 新版实板测试未进行');c.drawRightString(547,34,f'{number} / 4')
    c.bookmarkPage(f'p{number}');c.addOutlineEntry(title,f'p{number}',0)

page(1,'让存下来的证据保持一致','本报告是 V1.32 完整项目技术手册的增补。它记录一次范围明确的可靠性修复，不替代算法、硬件和历史实板章节。')
p('结论','h')
p(f"V1.33 已通过 {S['unit_tests']['count']} 项主机回归、{S['front_end']['tests']} 项前端状态测试，以及四个真实进程异常退出阶段和双进程冲突验证。修复了并发保存时，失败写者可能覆盖已提交图片的问题。")
table(['产品层次','本版实际变化'],[
 ['FPGA / PL','沿用 V1.32 下载文件和逻辑：720p60 图像处理、裂纹候选、区域框、产品跟踪、最佳帧选择。算法没有移到电脑。'],
 ['ARM / Vitis','沿用 V1.32 固件（0x12000），继续负责 DMA、缓存、压缩、网络与确认。没有修改固件计算。'],
 ['电脑工作站','将保存前的身份检查、容量检查、两张 PNG 发布、数据库登记和待确认登记串行化，防止不同进程同时写坏同一条证据。']])
p('验收边界','h')
p('本轮没有枚举到 USB/JTAG 设备，直连地址的 TCP 连接也超时，因此没有新上板验收。BIT、XSA、LTX、ELF 与已实板验证的 V1.32 逐字节一致；新 Vivado 工程已生成并完成 BD 校验。不能把这些结果说成 V1.33 新硬件通过实测。')
p('版本备份','h')
p('修改前核对了 V1.32 的 773 个源码文件及其封存证据，并生成 835 项文件的轻量 ZIP，逐项核对 SHA256。原工程和原数据全部保留；ZIP 以源码、交付文件、报告为主，不是全部运行素材的副本。')

page(2,'问题为什么会发生','同一个“保存”动作横跨图片文件与数据库。只保护某一个 Python 对象，无法协调另一进程。')
p('旧版已复现的失败顺序','h')
table(['时刻','旧版行为'],[
 ['1 · 写者 A','查询编号，发现没有记录；暂停在写图之前。'],
 ['2 · 写者 B','查询同一编号，也发现没有记录；保存另一张图，提交记录，并完成人工复核。'],
 ['3 · 写者 A 继续','先覆盖 PNG，再尝试插入数据库；编号唯一性约束拒绝了插入，但图片已经被覆盖。'],
 ['4 · 读取证据','数据库是 frame 74，图片却来自失败的 frame 73；SHA256 检查发现不一致。已有备注仍在，图却错了。']])
p('V1.33 的保存顺序','h')
p('取得 SQLite 写事务 → 检查编号和已有内容 → 检查容量 → 发布原图与掩码 → 写入事件及待确认记录 → 提交。第二个写者必须等待，等到前一个提交后，再读取最新身份。如果内容冲突，在触碰图片前拒绝。')
p('为什么采用 BEGIN IMMEDIATE','h')
p('BEGIN IMMEDIATE 会立即申请数据库写事务。SQLite 同一时刻只允许一个写者；因此遵循本程序保存流程的多个连接会排队。WAL 模式允许读者读取已提交内容，图像发布期间尚未提交的新记录不会出现在列表中。[1][2]')
p('关键限制','h')
p('数据库回滚不能撤销任意 PNG 文件操作。本版解决的是并发覆盖；若新记录写到一半进程终止，未登记的 PNG 仍可能留下。它们不会冒充已提交记录，也不会触发持久化确认；后续同编号重试可以恢复。物理断电一致性仍需额外设计。')

page(3,'怎样证明修复有效','测试既检查成功路径，也主动制造冲突、写入失败和进程退出。所有破坏性操作只作用于隔离测试目录。')
table(['验证项目','观测结果'],[
 ['旧版失败复现','可重复制造先覆盖图片、后 UNIQUE 失败；报告保存了提交摘要与实际摘要，二者不同。'],
 ['10 项新增专项','同编号不同决策、不同图像、不同掩码拒绝；同内容幂等；跨连接容量检查；忙锁、写图失败、确认失败、提交失败均释放事务。'],
 ['真实独立进程','第二写者等待；第一写者提交后，第二写者在写图前拒绝。获胜图片保持原字节。'],
 ['第 1 / 第 2 图后退出','新事件和待确认记录均未提交；已人工审核的旧证据完整；重启后同编号可重试。'],
 ['事件 INSERT 后退出','未提交数据库事务恢复后不可见；没有持久化待确认身份；重试恢复。'],
 ['实际 COMMIT 后退出','事件与待确认身份都存在；同内容重试不改变创建时间或原图。'],
 ['全套回归',f"主机 {S['unit_tests']['count']} 项、前端 {S['front_end']['tests']} 项全部通过，覆盖传输校验、ACK、恢复、复核、状态同步等。"]])
p('测试环境与证据','h')
p('Python 3.12.14，SQLite '+S['sqlite_version']+'，Windows。本轮使用真实 SQLite、真实 PNG 和真实子进程退出；没有模拟成已完成的物理断电试验。完整机器可读证据位于 reports/v133/validation_summary.json；逐条日志为 host_tests.log。','small')
p('四个退出点的 SQLite 完整性检查均为 ok。以原图、掩码哈希以及人工复核状态和修订号共同判断旧证据是否保持，而不是只检查函数有没有报错。','small')

page(4,'使用、回退与后续迭代','本版工程：D:/Vivado/pynq_z2_tile_v1_53。不要同时启动两个版本争用同一开发板。')
p('怎么运行与回退','h')
p('电脑端入口仍是“启动以太网工作站.bat”。默认仅预览、不自动留图，存档上限 1 GiB。运行前确认板端装载兼容 V1.32 BIT/ELF；若板卡已断电，可用本版 .sdk/program_ethernet.bat 重新下载。当前尚未重新下载。')
p('本版 .sdk 保留可下载的原版 BIT/XSA/LTX/ELF 及软件源代码。Vivado XPR 是新生成的可编辑工程；Vitis 平台与 BSP 如需重新生成，运行 .sdk/build_ethernet.py。不要把修改固件后的 ELF 与继承的验收哈希混用。')
p('需要回退时，先停止当前接收和服务，再进入原 V1.32 目录启动；板端逻辑未变，无需仅因电脑端回退而更换算法。轻量备份位于 D:/Vivado/_baseline_backups/tile_v1_32_before_v1_33.zip。')
p('下一版：降低普通预览的流量','h')
p('历史 60 秒实板场景接收了 525 帧，只归档 10 条最佳证据。计划让普通预览可选 2 / 5 fps，报警队列和人工抓拍优先处理。FPGA 仍持续检测。这是待验证的方向，尚未计入本版完成项；首先用可控事件和真实 TCP 测试，之后再做板上对照。')
p('术语小课堂','h')
p('事务：一组数据库修改一起提交或一起撤回。竞态：结果依赖两个操作碰巧的先后顺序。幂等：同一内容重试不会新增或改坏原记录。SHA256：文件摘要，用来比较保存前后字节是否一致。孤立文件：文件已存在，但数据库没有对应记录。ACK：电脑告诉板端某一事件已经处理完，板端才可释放相应缓存。')
p('原理来源与阅读入口','h')
p('[1] SQLite Transaction: https://www.sqlite.org/lang_transaction.html\n[2] SQLite WAL: https://www.sqlite.org/wal.html\n[3] Python os.fsync: https://docs.python.org/3/library/os.html#os.fsync\n原项目体系、公式及硬件算法详见 V1.32 的 59 页完整技术手册。','small')
c.save()
dest=R/'docs'/pdf.name;shutil.copy2(pdf,dest)
(O/'pdf_layout.json').write_text(json.dumps(dict(pages=4,minimum_content_y=min(bottoms),pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest()),indent=2),encoding='utf-8')
print(str(pdf))
