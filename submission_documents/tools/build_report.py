"""Competition-template report. ZIP patch preserves the supplied document furniture.
Run with managed Python. Uses actual frozen source/results, never synthetic evidence.
"""
from pathlib import Path
from copy import deepcopy
import argparse, hashlib, json, re, zipfile, shutil, math
from lxml import etree as E
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic':'http://schemas.openxmlformats.org/drawingml/2006/picture'}
def q(n):a,b=n.split(':');return '{'+NS[a]+'}'+b
def el(n,**attrs):
    e=E.Element(q(n))
    for k,v in attrs.items():e.set(q('w:'+k),str(v))
    return e
def sha(b):return hashlib.sha256(b).hexdigest()
def font(sz):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',sz)

LIMITS={
'abstract':(800,'本作品面向流水线末端的瓷砖表面裂纹检查，构建了基于 PYNQ-Z2 的 FPGA 检测、板端证据采集和电脑人工复核系统。产品连续经过视野时，FPGA 实时生成裂纹候选掩码与局部红框，识别产品编号并选择完整、居中的最佳报警帧；ARM 处理器负责把证据送到电脑，电脑保存原图、掩码、参数及校验值，供人工确认和追溯。\n当前版本为 V1.53.1，固定输入 1280×720、60 帧/秒，使用真实瓷砖照片通过电脑 HDMI 连续运动回放进行实板测试。像素级计算采用四方向暗谷响应、双尺度弱支持、双阈值及有限级邻域传播；区域合并和最佳帧选择也在 FPGA 中完成。Vitis 程序采用散聚 DMA、DDR 缓冲、有限事件队列及无损打包传输，不承担裂纹识别。电脑端在图像持久保存后确认板端事件，支持校验、重连、复核和容量管理。\n历史开发样本中，17 张裂纹照片均产生报警，33 张正常照片均未报警；双尺度方案的裂纹像素召回率为 28.20%。另一个未调参的大理石测试集仅有 1/24 张产生报警，说明当前算法依赖材质和成像条件。120 秒连续运动实板测试保存 20 个产品的 20 张自动证据，输入处理约 60.09 帧/秒，采集间隙等五类错误计数增量均为零。作品已形成可演示、可复现的竞赛原型；后续需接入真实相机、固定照明并完成独立工业测试，才能评估工厂应用。'),
'function':(400,'系统完成连续视频输入、裂纹候选检测、显示红框、按产品保存最佳证据及电脑人工复核。FPGA 每帧处理像素，不要求瓷砖在视野中央停下；产品离站后发布最佳报警图。电脑可切换原图与掩码，查看产品号、帧号、材料参数和校验状态，将记录标为确认裂纹、误报或需复查，并导出结果。仅预览模式避免长期测试持续写盘；自动留图受容量限制。红框是候选异常的位置，最终结论仍需人工审核。'),
'application':(400,'预期应用为单通道流水线末端的平面瓷砖表面检查，也可作为 FPGA 视频处理教学平台。当前已验证场景为电脑 HDMI 输入的真实瓷砖照片及连续移动回放，主要适用于经过参数标定、裂纹表现为局部暗线的材料。尚未验证实体输送带、真实相机、工厂光照、不同尺寸及连续贴合产品，不宣称可直接替代工业质检。未来需通过样品、照明和触发器把像素指标转换为实际毫米精度与产线速度。'),
'features':(400,'第一，灰度计算、裂纹候选、区域定位、产品编号及最佳帧排序均在可编程逻辑中执行，避免 ARM 逐像素识别。第二，检测与取图分离：像素流水线持续运行，DMA 和 DDR 缓冲承担采集，电脑按需接收报警图。第三，帧号、启动身份、恢复代次、参数与校验值随图传输，避免把红框套到错误图像。第四，采用灰度整数运算、行缓存和有限级邻域支持，适合 FPGA 实现。第五，保留已校准样本与外部留出集的不同结果，明确跨材质漏检问题。'),
'metrics':(200,'指标\t实测或设计值\n输入\t1280×720，60 帧/秒\n运动验收\t120 秒，20 个产品留图\n处理帧率\t约 60.09 帧/秒\n区域上限\t8 个\n事件队列\t12 个\nLUT / BRAM\t32.72% / 74.64%\nWNS\t+0.030 ns\n统计均限于本报告测试条件。'),
'innovation':(200,'（1）将弱裂纹支持和按产品最佳证据选择一并放入 FPGA，连续运动时无需停线取图。\n（2）用同帧元数据、像素校验和落盘后确认建立可追溯证据链。\n（3）针对难压缩图像压紧颜色与掩码，减少 21.875% 传输字节。以上为作品工程特点，不作专利或首创性声明。'),
'process':(200,'先实现 HDMI 直通并上板确认时钟，再加入灰度、暗谷和弱裂纹支持；随后实现区域框、按产品留图、DMA 与以太网传输；最后补充同步校验、重连恢复、存储和复核功能。每轮保留旧工程，以软件参考模型、自动测试和实板输入逐步验收，冻结可复现提交版。'),
'extension':(300,'优先固定照明与相机曝光，建立独立标注的正常、裂纹和干扰样本，按材质评估误报与漏检。然后加入线体触发或编码器，解决贴合产品编号问题，实测运动模糊与毫米精度。算法可探索局部归一化、方向一致性和更细区域连接；先量化收益，再决定是否更换更大 FPGA。传输可评估裁剪证据与缩略图，但保留完整原图供审核。通过真实故障注入和长时间运行验证电源重启、磁盘写满及网络中断，完善部署可靠性。'),
'reflection':(1000,'设计过程说明，能综合并生成比特流只证明电路可以实现，并不证明裂纹检测有效。必须先看真实 HDMI 采集和帧号，再对照参考模型检查像素，最后检验报警图是否完整、是否属于同一产品。时钟、同步、数据缓冲和算法精度是不同问题，不能用一个“通过”代替全部验收。\n本工程的流水线并不是让产品停在中央：它指硬件模块在不同时钟周期并行处理不同像素。有限行缓存支持邻域计算，帧图像由 DDR 保存。电脑取图变慢时，FPGA 仍可继续检测，但有限的事件缓存最终会满，因此必须明确队列和丢失计数，而不是承诺无限缓存或永不丢失。\n弱裂纹增强也存在边界。保持高阈值种子、增加低阈值支持，可以连接部分弱响应；一味降低阈值会把纹理和阴影一起选中。已调参瓷砖的报警效果好，不代表外部大理石同样有效。外部测试结果较差时，应该保留数据并解释原因，重新设计成像和评估流程，不能把测试集继续调参后的成绩当作独立准确率。\n提交材料应让评审区分设计值、实测值和未来计划。当前已经形成由 FPGA 检测、Vitis 采集传输、电脑复核组成的完整原型，但真实相机、机械结构和工厂验证仍属于下一阶段。通过保留版本、脚本、原始测试记录和数据来源，作品可以被重新运行和检查，也便于答辩时说明每一项功能由哪一部分实现。')}

def diagrams(assets, project):
    assets.mkdir(exist_ok=True)
    def text(d,xy,s,size=38,center=False):
        d.multiline_text(xy,s,font=font(size),fill='#20242a',anchor='mm' if center else None,align='center' if center else 'left',spacing=12)
    def box(d,rect,s):
        d.rectangle(rect,fill='#f2f5f8',outline='#65717d',width=3)
        text(d,((rect[0]+rect[2])/2,(rect[1]+rect[3])/2),s,38,True)
    def arrow(d,a,b):
        d.line([a,b],fill='#37414d',width=4)
        theta=math.atan2(b[1]-a[1],b[0]-a[0]);L=18
        p=[b,(b[0]-L*math.cos(theta-.45),b[1]-L*math.sin(theta-.45)),(b[0]-L*math.cos(theta+.45),b[1]-L*math.sin(theta+.45))]
        d.polygon(p,fill='#37414d')
    im=Image.new('RGB',(1600,690),'white');d=ImageDraw.Draw(im)
    box(d,(30,50,430,200),'电脑 HDMI 信号源\n真实照片连续回放')
    box(d,(600,50,1030,200),'PYNQ-Z2\nFPGA 检测与选帧')
    box(d,(1210,50,1570,200),'HDMI 显示器\n原图及红框')
    arrow(d,(430,125),(600,125));text(d,(515,80),'HDMI IN',27,True)
    arrow(d,(1030,125),(1210,125));text(d,(1120,80),'HDMI OUT',27,True)
    box(d,(600,310,1030,465),'板上 ARM 与 DDR\n采集  校验  传输')
    box(d,(30,310,430,465),'电脑复核工作站\n保存  审核  导出')
    arrow(d,(815,200),(815,310));text(d,(1100,260),'AXI DMA 写入图像',30,True)
    arrow(d,(600,385),(430,385));text(d,(515,340),'网线',28,True)
    text(d,(800,560),'USB 接 PROG UART：下载调试与串口；不承担整帧视频传输',35,True)
    text(d,(800,625),'当前是 HDMI 回放验证；真实相机、光源与输送带属于后续接入',34,True)
    im.save(assets/'system.png')
    im=Image.new('RGB',(1600,820),'white');d=ImageDraw.Draw(im)
    rects=[(40,40,480,190),(580,40,1020,190),(1120,40,1560,190),
           (1120,315,1560,465),(580,315,1020,465),(40,315,480,465)]
    labels=['TMDS 解码\n像素与同步信号','灰度与行缓存\n双尺度暗谷响应','强弱阈值\n四级邻域支持','32×32 网格连通\n最多 8 个区域框','产品编号与排序\n完整入镜优先','采集原图与掩码\n同帧描述和 CRC']
    for r,s in zip(rects,labels):box(d,r,s)
    for a,b in [((480,115),(580,115)),((1020,115),(1120,115)),((1340,190),(1340,315)),((1120,390),(1020,390)),((580,390),(480,390))]:arrow(d,a,b)
    box(d,(40,615,620,755),'显示支路\n像素叠框 → TMDS 编码')
    box(d,(840,615,1560,755),'证据支路\nFIFO → SG DMA → DDR')
    arrow(d,(260,465),(260,615));arrow(d,(480,460),(1200,615))
    im.save(assets/'pl.png')
    im=Image.new('RGB',(1600,940),'white');d=ImageDraw.Draw(im)
    labels=['预置 SG 描述符\n32 个 BD，48 个 DDR 槽','接收完整帧\n检查状态与描述 CRC','TCP 发送事件\n断开后保留未确认证据','遵循 PL 产品标志\n保留最佳槽，离站发布','电脑校验并持久保存\n原图  掩码  数据库','确认具体事件\n板端释放对应槽引用']
    for i,s in enumerate(labels):
        col=i%2;row=i//2;x=50+col*820;y=30+row*300;box(d,(x,y,x+680,y+180),s)
    for a,b in [((730,120),(870,120)),((1210,210),(1210,285)),((870,420),(730,420)),((390,510),(390,630)),((730,720),(870,720))]:arrow(d,a,b)
    text(d,(800,910),'循环继续采集；网络与写盘的等待不让像素流水线停下来',34,True)
    im.save(assets/'evidence_flow.png')
    # Genuine board captures: overlay ONLY actual PL boxes in the matching summary.
    result=json.loads((project/'reports/v153/real_board_wide/summary.json').read_text(encoding='utf-8'))
    item=result['items'][0];src=project/'reports/v153/real_board_wide/real_000_original.png'
    orig=Image.open(src).convert('RGB');annot=orig.copy();dd=ImageDraw.Draw(annot)
    for b in item['frame']['boxes']:dd.rectangle(b,outline='red',width=4)
    mask=Image.open(project/'reports/v153/real_board_wide/real_000_mask.png').convert('RGB')
    im=Image.new('RGB',(1560,1060),'white');d=ImageDraw.Draw(im)
    im.paste(annot.resize((1500,844)),(30,90));text(d,(780,40),'实板原图叠加同帧 PL 区域框',40,True)
    text(d,(780,985),f"帧 {item['frame']['frame_id']}  候选 {item['frame']['candidate_pixels']} 像素  参数 90 / 45",36,True)
    im.save(assets/'board_capture.png')
    # Compact actual mask, no claim of ground truth or complete crack extraction.
    mask.resize((1280,720)).save(assets/'board_mask.png')
    (assets/'evidence_sources.json').write_text(json.dumps({'overlay_original':str(src.relative_to(project)),
      'overlay_summary':'reports/v153/real_board_wide/summary.json','frame':item['frame']['frame_id'],
      'boxes':item['frame']['boxes'],'original_sha256':sha(src.read_bytes()),
      'scope':'Actual HDMI/PL capture; boxes are drawn from same frame metadata, not a physical assembly photograph.'},ensure_ascii=False,indent=2),encoding='utf-8')
    if (HERE/'workstation_review.jpg').exists():shutil.copy2(HERE/'workstation_review.jpg',assets/'workstation_review.jpg')

def build(reference, project, output):
    assert sha(reference.read_bytes())=='d15a2aa186f600cb9c234bffd9deff0c4e9b05c569643d8a81d536f66f424f0c'
    assets=HERE.parent/'assets';diagrams(assets,project)
    source=zipfile.ZipFile(reference);parts={n:source.read(n) for n in source.namelist()}
    root=E.fromstring(parts['word/document.xml']);body=root.find('w:body',NS)
    paras=body.findall('w:p',NS);sect=deepcopy(body.find('w:sectPr',NS));new=[]
    relroot=E.fromstring(parts['word/_rels/document.xml.rels']);relNS='http://schemas.openxmlformats.org/package/2006/relationships'
    # The supplied template incorrectly continues 1.7 in Part 2. Clone its
    # actual list pattern with base level starting at 2, preserving originals.
    numbering=E.fromstring(parts['word/numbering.xml'])
    clone=deepcopy(numbering.find("w:abstractNum[@w:abstractNumId='1']",NS));clone.set(q('w:abstractNumId'),'3')
    clone.find('w:nsid',NS).set(q('w:val'),'5411AB07');clone.find('w:tmpl',NS).set(q('w:val'),'5411AB07')
    clone.find("w:lvl[@w:ilvl='0']/w:start",NS).set(q('w:val'),'2')
    first_num=numbering.find('w:num',NS);numbering.insert(list(numbering).index(first_num),clone)
    instance=el('w:num',numId='4');instance.append(el('w:abstractNumId',val='3'))
    numbering.append(instance)
    images=[];checks={}
    def paragraph(text='',template=7,size=None,bold=False,center=False,keep=False,page=False):
        p=deepcopy(paras[template]);pr=p.find('w:pPr',NS)
        if pr is None:pr=el('w:pPr');p.insert(0,pr)
        for ch in list(p):
            if ch is not pr:p.remove(ch)
        # Editable plain body never inherits template list numbering or red guidance.
        if template==7:
            for x in pr.findall('w:numPr',NS):pr.remove(x)
            ind=pr.find('w:ind',NS)
            if ind is not None:pr.remove(ind)
        for tag in ('keepNext','keepLines','pageBreakBefore','jc'):
            for x in pr.findall('w:'+tag,NS):pr.remove(x)
        if keep:pr.append(el('w:keepNext'))
        pr.append(el('w:widowControl'))
        if page:pr.append(el('w:pageBreakBefore'))
        if center:
            pr.append(el('w:jc',val='center'))
            for x in pr.findall('w:ind',NS):pr.remove(x)
            pr.append(el('w:ind',left='0',right='0',firstLine='0',firstLineChars='0'))
        r=el('w:r');rp=el('w:rPr');rp.append(el('w:rFonts',ascii='Times New Roman',hAnsi='Times New Roman',eastAsia='宋体'))
        rp.append(el('w:color',val='000000'));rp.append(el('w:sz',val=(size or (18 if template==0 else 12))*2))
        rp.append(el('w:szCs',val=(size or 12)*2))
        if bold:rp.append(el('w:b'))
        r.append(rp)
        for j,line in enumerate(text.split('\n')):
            if j:r.append(el('w:br'))
            t=el('w:t');t.text=line;t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');r.append(t)
        p.append(r);return p
    def p(t,**kw):new.append(paragraph(t,**kw))
    def limited(key):
        limit,t=LIMITS[key];n=len(re.sub(r'\s','',t));assert n<limit,(key,n,limit)
        checks[key]={'characters_without_spaces':n,'limit':limit};return t
    def h(t,slot,page=False):
        p(t,template=slot,size=14 if slot in [5,24,39,50,58] else 12,bold=True,keep=True,page=page)
        if slot in (27,30,35):new[-1].find('w:pPr/w:numPr/w:numId',NS).set(q('w:val'),'4')
    def sub(t):p(t,bold=True,keep=True)
    def fig(name,caption,width=5.75):
        path=assets/name;im=Image.open(path);cx=int(width*914400);cy=int(cx*im.height/im.width)
        rid='rIdTileLab'+str(len(images)+1);target='media/tilelab_'+name
        rel=E.SubElement(relroot,'{'+relNS+'}Relationship');rel.set('Id',rid);rel.set('Type',NS['r']+'/image');rel.set('Target',target)
        images.append(('word/'+target,path.read_bytes()))
        fp=paragraph('',center=True,keep=True);r=fp.find('w:r',NS);dr=E.SubElement(r,q('w:drawing'));inline=E.SubElement(dr,q('wp:inline'),distT='0',distB='0',distL='0',distR='0')
        E.SubElement(inline,q('wp:extent'),cx=str(cx),cy=str(cy));E.SubElement(inline,q('wp:effectExtent'),l='0',t='0',r='0',b='0')
        E.SubElement(inline,q('wp:docPr'),id=str(100+len(images)),name='TileLab '+name,descr=caption)
        E.SubElement(inline,q('wp:cNvGraphicFramePr'))
        graphic=E.SubElement(inline,q('a:graphic'));gd=E.SubElement(graphic,q('a:graphicData'),uri=NS['pic']);pic=E.SubElement(gd,q('pic:pic'))
        nv=E.SubElement(pic,q('pic:nvPicPr'));E.SubElement(nv,q('pic:cNvPr'),id='0',name=name);E.SubElement(nv,q('pic:cNvPicPr'))
        bf=E.SubElement(pic,q('pic:blipFill'));bl=E.SubElement(bf,q('a:blip'));bl.set(q('r:embed'),rid)
        stretch=E.SubElement(bf,q('a:stretch'));E.SubElement(stretch,q('a:fillRect'))
        sp=E.SubElement(pic,q('pic:spPr'));xf=E.SubElement(sp,q('a:xfrm'));E.SubElement(xf,q('a:off'),x='0',y='0');E.SubElement(xf,q('a:ext'),cx=str(cx),cy=str(cy))
        geom=E.SubElement(sp,q('a:prstGeom'),prst='rect');E.SubElement(geom,q('a:avLst'))
        new.append(fp);p(caption,size=11,center=True)
    def table(headers,rows,widths):
        t=el('w:tbl');pr=el('w:tblPr');pr.append(el('w:tblW',w=sum(widths),type='dxa'));pr.append(el('w:tblLayout',type='fixed'))
        bs=el('w:tblBorders')
        for side in ('top','left','bottom','right','insideH','insideV'):bs.append(el('w:'+side,val='single',sz='4',color='D9D9D9'))
        pr.append(bs);m=el('w:tblCellMar')
        for side in ('top','left','bottom','right'):m.append(el('w:'+side,w='85',type='dxa'))
        pr.append(m);t.append(pr);g=el('w:tblGrid')
        for w in widths:g.append(el('w:gridCol',w=w))
        t.append(g)
        for i,row in enumerate([headers]+rows):
            tr=el('w:tr');trpr=el('w:trPr');trpr.append(el('w:cantSplit'))
            if i==0:trpr.append(el('w:tblHeader'))
            tr.append(trpr)
            for j,val in enumerate(row):
                tc=el('w:tc');cp=el('w:tcPr');cp.append(el('w:tcW',w=widths[j],type='dxa'));cp.append(el('w:vAlign',val='center'))
                cp.append(el('w:shd',fill='E8EDF2' if i==0 else ('F8F9FA' if i%2==0 else 'FFFFFF')));tc.append(cp)
                tp=paragraph(str(val),size=11,bold=i==0,center=(j>0 and len(str(val))<35))
                pp=tp.find('w:pPr',NS)
                for x in pp.findall('w:ind',NS):pp.remove(x)
                pp.append(el('w:ind',left='0',right='0',firstLine='0',firstLineChars='0'))
                sp=pp.find('w:spacing',NS)
                if sp is None:sp=el('w:spacing');pp.append(sp)
                sp.set(q('w:line'),'280');sp.set(q('w:after'),'0');sp.set(q('w:before'),'0');tc.append(tp);tr.append(tc)
            t.append(tr)
        new.append(t);p('')
    p('基于 FPGA 的瓷砖裂纹检测与证据留存系统',template=0,size=18,bold=True,center=True)
    p('技术报告  V1.53.1  2026年10月9日',size=12,center=True)
    h('摘要',2)
    p(limited('abstract'))
    h('第一部分  作品概述',5,page=True)
    h('功能与特性',6);p(limited('function'))
    h('应用领域',9);p(limited('application'))
    h('主要技术特点',12);p(limited('features'))
    h('主要性能指标',15);limited('metrics')
    table(['指标','实测或设计值'],[['输入','1280×720，60 帧/秒'],['运动验收','120 秒，20 个产品留图'],['处理帧率','约 60.09 帧/秒'],['区域上限 / 事件队列','8 个 / 12 个'],['LUT / BRAM','32.72% / 74.64%'],['WNS','+0.030 ns']],[3500,4806])
    p('统计均限于本报告测试条件。',size=11)
    h('主要创新点',18);p(limited('innovation'))
    h('设计流程',21);p(limited('process'))
    h('第二部分  系统组成及功能说明',24,page=True)
    h('整体介绍',27)
    p('系统按职责分为可编程逻辑、板端软件和电脑工作站三层。PYNQ-Z2 内的 Zynq-7000 同时包含 FPGA 逻辑区 PL 与 ARM 处理器区 PS：PL 是并行电路，PS 运行程序。[1] 本作品把检测留在 PL，把图像搬运、网络及管理留给 PS 与电脑。')
    fig('system.png','图 1  系统组成及当前实际接口关系')
    p('信号源电脑向 HDMI IN 输出 720p60。开发板恢复像素后进行检测，同时由 HDMI OUT 输出原图和区域框。检测证据经板上 DDR 暂存，通过以太网送往电脑，浏览器访问本机工作站进行复核。USB 接 PROG UART，供 JTAG 下载和串口调试使用。普通 USB 摄像头不会天然输出 HDMI；后续相机应提供兼容 HDMI 输出，或另行设计输入转换，不能把任何摄像头直接等同于当前信号源。')
    p('为区分速度指标，本报告使用“检测帧率”表示 PL 处理输入的速度，使用“取图耗时”表示一张证据在网络和主机上的请求时间。普通电脑预览默认最多请求 2 帧/秒，这只是省流设置；FPGA 仍处理每一帧 60 帧/秒的视频。报警事件优先接收，但有限队列不能承诺在无限停收条件下不丢失。')
    h('硬件系统介绍',30)
    sub('2.2.1 硬件整体介绍')
    p('硬件基于现成 PYNQ-Z2 开发板，器件为 xc7z020clg400-1。Vivado 工程以 system Block Design 和 system_wrapper 为顶层，连接 Processing System、AXI 控制总线、视频处理模块、AXI DMA 及调试接口。TMDS 解码与编码使用 Digilent 的 dvi2rgb / rgb2dvi IP。[2] 自研 RTL 负责像素检测、同步、区域统计、产品识别和采集描述。')
    fig('pl.png','图 2  FPGA 视频处理及两条输出支路')
    sub('2.2.2 机械设计介绍')
    p('本阶段没有自制输送带、相机支架、机壳或 CAD 结构。当前利用真实照片的匀速 HDMI 回放验证连续运动输入，照片经过视野时不专门停顿。这能验证像素计算、产品留图和传输流程，但不能证明实体运动模糊、照明均匀性或机械安装精度。工程接入真实产线后，应增加固定支架、遮光及漫射照明，并根据输送带速度和相机视野配置曝光与触发。')
    sub('2.2.3 电路模块与时钟设计')
    p('TMDS 是 HDMI 使用的串行信号编码方式。解码器把串行输入还原为 24 位颜色数据、像素时钟以及 de、hs、vs：de 表示当前位置有有效图像，hs 和 vs 分别表示行、帧同步。计算模块必须把这些同步信号和图像延迟相同的周期数，否则框和图会错位。')
    table(['时钟或信号','当前配置','作用'],[['恢复像素时钟','74.25 MHz','视频像素流水线'],['输出串行时钟','371.25 MHz','OSERDES 双沿发送'],['单颜色 TMDS 数据率','742.5 Mb/s','10 位编码 / 像素'],['PS FCLK0','100 MHz','AXI / DMA 总线'],['PS FCLK1','200 MHz','参考及控制域']],[2900,1900,3506])
    p('720p60 的完整光栅包括消隐，横向 1650 个时钟、纵向 750 行，因此 1650×750×60=74.25 MHz；有效图像只是 1280×720。每个 8 位颜色通道编码为 10 位串行符号，输出使用 5 倍像素时钟并在双沿发送。输出编码器由自己的 MMCM 产生串行时钟，避免跨 I/O 区共享接收 BUFIO 时钟造成放置问题；kClkRange=2 对应 742.5 MHz 的 MMCM VCO。')
    p('跨时钟域 CDC 指信号从一个时钟控制的电路进入另一个时钟域。控制配置通过 config_bridge 传递，并在帧边界生效；图像采集通过异步 FIFO 进入 DMA 域。约束文件声明不同来源时钟的关系，复位必须与各域同步设计配合。时钟组约束不能代替正确的跨域电路。当前布线后 WNS 只有 +0.030 ns，说明时序余量较小，尚无提高频率的验收依据。')
    sub('2.2.4 灰度与裂纹响应')
    p('灰度把红、绿、蓝三个颜色数转换为一个亮度数，降低电路计算量。源 RGB 通道先按接口次序对齐，再采用整数近似：')
    p('Y = floor((77R + 150G + 29B) / 256)',center=True)
    p('R、G、B 为 0～255 的颜色值，floor 表示向下取整。系数之和为 256，除法可用右移 8 位实现。PL 的行缓存保留邻近行，在连续输入下形成邻域窗口；不用让 ARM 先读整幅图再计算。')
    p('暗裂纹通常比两侧表面暗。对像素位置 p，沿水平、竖直和两个斜向 d，在距离 r 的两侧取灰度。先取两侧较暗的值，再在四个方向选最大值，最后减去中心亮度并限制为非负：')
    p('Dᵣ(p) = max(0, max₍d₎ min(Y(p+rd), Y(p−rd)) − Y(p))',center=True)
    p('取两侧最小值，要求中心两边都较亮，减少单边边缘被当作裂纹；选四个方向的最大值，让不同方向的裂纹都有机会响应。r=8 产生强裂纹种子，r=16 只提供可选的弱支持。两路通过精确的光栅延迟对齐。它是基于局部灰度的传统算法，没有训练神经网络，也不属于 YOLO。')
    sub('2.2.5 双阈值与有限邻域支持')
    p('高阈值 T_H 确定强响应；低阈值 T_L=ceil(T_H/2)，ceil 表示向上取整。当前真实照片配方为 90 / 45，比较采用严格大于阈值。启用双尺度时：')
    p('S(p) = [D₈(p) > T_H]\nW(p) = [max(D₈(p), D₁₆(p)) > T_L]',center=True)
    p('方括号表示条件成立为 1，否则为 0。S 是强种子，W 是弱候选。四级 3×3 邻域支持从 A₀=S 开始，每一级只允许有足够已接受邻居的弱候选加入：')
    p('Aₖ₊₁(p) = Aₖ(p) OR (W(p) AND Σ₍q∈N₃×₃₍p₎₎ Aₖ(q) ≥ 3)',center=True)
    p('N 是中心附近九个位置；OR 和 AND 表示逻辑“或”和“且”。有效图像和 ROI 之外及边界强制为零。四级最多向外传播四个像素，不反复扩散到整片纹理。这与无限迭代的连通生长不同，硬件延迟固定。弱候选附近完全没有强种子时仍会漏检，因此该方法不能保证找到所有微弱裂纹。')
    sub('2.2.6 区域框与产品最佳证据')
    p('region_grid 把候选图划分为 32×32 像素网格，记录每格候选数量和精确坐标极值，在消隐期对占用格做八邻域连通合并。八邻域包括上下左右和四个斜向。输出最多 8 个框，框边界来自实际候选像素；但相近裂纹可能在网格尺度合并，超过上限或分析异常会设置状态标志，不能默认为无缺陷。')
    p('product_tracker 用中心列的亮表面门禁识别产品进入，两个有效的无产品帧确认离站。无效采集属于未知观察，不启动、不结束产品，也不更改最佳帧。每个产品优先保留完整入镜的报警帧，再选择最居中的帧；只有排序相同时才比较候选面积。中心距离计算为：')
    p('d = |x_min + x_max − 1279|；中心误差 = d / 2 像素',center=True)
    p('完整入镜条件为 x_min>80 且 x_max<1199。尚未完整入镜时的回退优先比较候选面积，再比较距离。排序及更新标志均由 PL 输出，ARM 只保留对应 DDR 槽。产品必须有可分辨的间隙；贴合瓷砖、深色背景相似产品和多通道线体需要外部触发或改进门禁。HDMI 显示支路使用上一帧区域框，运动时存在一帧位置滞后；电脑归档框与图像取同一帧描述。')
    h('软件系统介绍',35)
    sub('2.3.1 软件整体介绍')
    p('软件分为 Vitis 的裸机应用和电脑工作站。Vitis 工程使用 .sdk 文件夹作为工作区，包含 FSBL、BSP、platform 和 hdmi_ethernet 应用。FSBL 为首次启动加载程序；BSP 提供器件驱动；platform 描述处理器、硬件接口与运行域。电脑侧 Python 服务管理接收与证据，网页提供操作界面，Windows 播放器负责向 HDMI 输出测试图。')
    fig('evidence_flow.png','图 3  Vitis 与电脑协作的证据采集确认流程')
    sub('2.3.2 Vitis 采集与传输模块')
    p('DMA 是直接存储器访问，用硬件搬运图像而不让 ARM 为每个像素执行复制指令。SG 即 Scatter/Gather，表示预先准备描述符，DMA 可按列表连续写入多个缓冲区。[3] 本工程预置 32 个 BD，使用 48 个 DDR 槽；每个完整帧 1280×720×4=3,686,400 字节。颜色、候选掩码与同帧描述进入采集流，数据槽的所有权由 DMA、事件队列及最佳证据引用共同管理。')
    p('acquisition() 处理完成的 BD，检查长度、帧边界及错误状态；consume() 验证 PL 描述并遵循产品开始、最佳更新和结束标志；finish_product() 发布最佳事件；apply_recipe_if_idle() 在产品空档提交参数；tile_network_poll() 轮询 TCP 连接。网络侧 reply() 生成带 CRC 的头部，pump() 分批发送，断线处理保留未确认事件。这些函数负责搬运与状态，不计算裂纹候选。')
    table(['模块','关键输入','关键输出'],[['采集消费','DMA 完成帧与 PL 描述','有效帧、槽引用、事件'],['产品留图','PL 编号与最佳更新标志','离站时发布最佳证据'],['材料参数','主机请求参数','空档提交及实采参数'],['网络发送','具体事件或预览请求','头部、图像、掩码'],['确认处理','启动身份与事件确认','释放匹配的已保存事件']],[2050,3128,3128])
    p('板端事件队列容量为 12 个。缓存满、采集缺口、无效帧、确认错误和描述 CRC 错误均分别计数。poll_recovery() 使用运行、复位、验证和失败状态处理采集异常，一次启动最多自动恢复 3 次；验证连续两张有效新图后才恢复正常。恢复代次随证据保存，旧事件不得被当作新采集成功。')
    sub('2.3.3 无损编码与速度边界')
    p('原始格式每像素使用 4 字节。难压缩图像采用 BGR24 加独立 1 位掩码，可降为 3.125 字节/像素；因此每帧从 3,686,400 降为 2,880,000 字节，节省 1−3.125/4=21.875%。可压缩画面使用游程压缩 RLE，把连续相同值表示为值及重复次数；这属于无损编码，主机解码后恢复同一规范像素流并校验 CRC。')
    p('若每一帧均发送原始图像，60 帧/秒约需 221.18 MB/s，即 1.77 Gb/s，已超过 1 Gb/s 网口的物理速率，尚未计协议开销。因此系统持续检测，但按产品发送证据并降低普通预览请求频率。减少字节不能自动证明降低时延：打包、网络、ARM 和主机解码都有成本，必须用同一个事件做对照。')
    sub('2.3.4 电脑留存与人工复核模块')
    p('电脑收到数据后检查启动身份、事件号、帧号、恢复代次、参数、头部 CRC、PL 描述 CRC 和规范像素 CRC，拒绝错配与损坏。原图和掩码写入临时文件，持久保存后提交数据库，再确认具体板端事件；网络断开后可重取同一个未确认事件，主机按身份去重，避免既丢证据又出现重复记录。')
    p('CRC 是循环冗余校验，用于发现数据错误，不用于抵抗恶意篡改。保存的 PNG 另记录 SHA-256 摘要，打开证据时复核文件内容。网页把框、掩码和图像绑定到同一帧；状态过期、播放器未采用请求或接收暂停时明确提示，不把保留画面标为当前实时图。人工结论由数据库保存，支持记录修订及导出。')
    p('仅预览不自动存图；自动留图达到容量上限后转为仅预览并记录未存事件，已保存证据不会自动被覆盖。磁盘盘点和图像内容校验分别标注。长期运行需按业务保留期限导出与清理证据，不能用删除全部数据替代容量管理。')
    h('第三部分  完成情况及性能参数',39)
    h('整体介绍',41)
    p('作品已完成真实开发板的视频输入检测、HDMI 叠框显示、以太网证据传输及电脑复核闭环。图 4 来自开发板真实采集，框坐标取自同一帧 PL 输出；图 5 为对应候选掩码。输入照片是真实材料，运动由电脑回放生成。本报告以这些实板数据和网页截图展示成果，不把它们称为实体产线或相机拍摄的现场试验。')
    fig('board_capture.png','图 4  HDMI 实板采集与同帧裂纹区域框')
    fig('board_mask.png','图 5  同帧 FPGA 候选掩码 白色为候选像素')
    p('本阶段使用裸开发板和现成接口，没有专用外壳或定制机械结构。比赛材料中的整机正面与 45° 视角照片，应在最终接线和演示布置后实拍；不能用系统框图或生成图片冒充实物照片。')
    h('工程成果',43)
    sub('3.2.1 机械成果')
    p('完成单通道连续运动的回放验证方法和接口布置设计；未制作实体输送带与相机机械系统。真实照片运动场景可用于复现，但实体产线机械性能不在当前验收范围内。')
    sub('3.2.2 电路成果')
    p('交付 Vivado 工程、Block Design、RTL、引脚与时序约束、从零创建脚本，以及比特流、XSA、LTX 和布线后报告。提交版 PL 与 Vitis ELF 使用已验收的 V1.52 基线；V1.53.1 更新电脑端验证和说明，没有重新改变电路频率或声称新增布线结果。RTL 和参考模型逐像素对照通过，不只依据综合无错误。')
    table(['资源','已使用 / 总量','占用率'],[['LUT','17408 / 53200','32.72%'],['触发器 FF','29175 / 106400','27.42%'],['BRAM Tile','104.5 / 140','74.64%'],['DSP','2 / 220','0.91%']],[2900,3500,1906])
    p('布线后 WNS=+0.030 ns、WHS=+0.050 ns。WNS 是最差建立时间余量，WHS 是最差保持时间余量；正值表示所分析路径满足相应约束。工程仍保留方法学警告，不能写成“所有警告为零”。BRAM 较紧张，后续加大窗口或缓存要先核算资源。')
    sub('3.2.3 软件成果')
    p('交付以 .sdk 为工作区的 Vitis 平台、BSP、FSBL、以太网应用及其源码和 ELF；电脑端包括工作站、连续运动播放器、自动测试、数据来源说明与第三方许可。另已完成技术与教学手册、详细视频拍摄方案及精简源码包。工程包经独立解压验证能够打开 Vivado 工程与 Vitis 工作区。')
    if (assets/'workstation_review.jpg').exists():
        fig('workstation_review.jpg','图 6  电脑复核界面实截 含 21 条已保存记录 当前接收暂停提示原样保留')
    p('复核页按产品号显示最佳证据，区分自动留图和人工抓拍，支持筛选及结论登记。图 6 的接收暂停状态是截图时的现场状态；不能据此推断正在接收，也不替代下面记录的固定测试窗口。正式拍摄前仍需重新检查线缆、连接和输入源。')
    h('特性成果',48)
    sub('3.3.1 图像算法验证')
    table(['测试','结果','解释'],[['开发回归 50 张','50/50 掩码与参考模型逐像素一致','验证 RTL 按预定规则运行'],['其中裂纹 17 张','17/17 报警','已开发调参样本'],['其中正常 33 张','0/33 报警','不是工厂误报率'],['双尺度像素指标','召回 28.20%；精确率 98.36%','仍漏掉较多标注裂纹像素'],['外部 MCS2 24 张','1/24 报警；像素召回 1.92%','未调参大理石；无正常样本']],[2450,3000,2856])
    p('像素召回率=TP/(TP+FN)，表示真实裂纹像素被选中的比例；像素精确率=TP/(TP+FP)，表示被选中的像素中有多少属于标注裂纹。TP 为正确选中的裂纹，FN 为漏检裂纹，FP 为误选背景。双尺度开发回归 TP=26523、FN=67520、FP=441。图像级报警只要求出现足够候选，不能用 17/17 报警声称整条裂纹都被提取。')
    p('真实瓷砖开发样本来源与许可保存在工程中，外部 MCS2 为独立的大理石裂纹数据。[4][5] 外部集没有正常图，不能估计其误报率。降低外部阈值虽能增加报警，但少量探索样本的像素精确率下降到约 9.13% 或 1.77%，因此未作为默认优化。后续应冻结独立留出集，使用合理照明和材质配方，再报告泛化效果。')
    sub('3.3.2 连续运动与同步验收')
    p('V1.53.1 的 120 秒实板测试使用真实照片合成流水线，经过实际 HDMI、PL、TCP、PNG 保存及数据库归档。得到 20 个自动事件，对应 20 个不同产品编号；保存图均通过校验，瓷砖完整入镜，最大中心误差 10 像素，输入处理估计为 60.085 帧/秒。采集间隙、无效帧、队列满丢失、确认错误及描述 CRC 错误的增量均为 0。这是本次窗口结果，不是无限运行或实体工厂的可靠性承诺。')
    sub('3.3.3 传输与软件验证')
    table(['场景','原始请求中位数','省流请求中位数'],[['真实照片 000','83.81 ms','61.63 ms'],['真实照片 005','83.81 ms','61.88 ms'],['噪声图','84.08 ms','86.09 ms']],[3300,2503,2503])
    p('50 个同一事件的编码对照确认恢复像素一致，噪声图有效载荷减少 21.875%，但打包时延略增。TCP 在传完数据、尚未确认时断开后，能够重连并取得同一个事件。最新主机自动测试共 438 项，437 项通过，1 项可选本地原生解码器测试跳过；不能表述为 438 项全部通过。故障测试包括协议截断、身份错配、重复确认、数据库与文件失败以及异步状态过期，部分为本地故障夹具，并不都代表实板硬件故障注入。')
    p('关键验收记录位于 reports/v153/real_board_wide、external_mcs2、transport_comparison.json 及 reports/v1531/submission_motion、host_tests.log。源代码、证据与冻结清单均保留哈希；本报告不提前填写未经发布验证的 GitHub 链接。')
    h('第四部分  总结',50,page=True)
    h('可扩展之处',53);p(limited('extension'))
    h('心得体会',55);p(limited('reflection'))
    h('第五部分  参考文献',58,page=True)
    refs=[
      '[1] AMD. Zynq 7000 SoC Technical Reference Manual UG585: Version 1.15[EB/OL]. (2026-02-06)[2026-10-09]. https://docs.amd.com/r/en-US/ug585-zynq-7000-SoC-TRM.',
      '[2] DIGILENT. Vivado Library: dvi2rgb and rgb2dvi IP[CP/OL]. [2026-10-09]. https://github.com/Digilent/vivado-library.',
      '[3] AMD. AXI DMA LogiCORE IP Product Guide PG021: Version 7.1[EB/OL]. [2026-10-09]. https://docs.amd.com/r/en-US/pg021_axi_dma.',
      '[4] MVTEC. MVTec Anomaly Detection Dataset[DB/OL]. [2026-10-09]. https://www.mvtec.com/research-teaching/datasets/mvtec-ad.',
      '[5] MACHINE LEARNING VISION RESEARCH GROUP. MCS2 Marble Crack Segmentation Dataset[DB/OL]. [2026-10-09]. https://github.com/MachineLearningVisionRG/mcs2-dataset.',
      '[6] TileLab 工程. V1.53.1 冻结源码与验收记录[Z]. 2026-10-09. 交付目录 project/pynq_z2_tile_v1_53；算法、传输及测试结论以该目录原始记录为准.'
    ]
    for r in refs:p(r)
    p('配套学习资料：最终提交版技术与教学手册详细解释 FPGA、时钟、RTL、灰度、邻域运算、DMA、协议、校验及人工复核；本报告按比赛模板概述作品，二者配套阅读。',size=11)
    for x in list(body):body.remove(x)
    for x in new:body.append(x)
    body.append(sect)
    def serialize(x):return E.tostring(x,xml_declaration=True,encoding='UTF-8',standalone=True)
    parts['word/document.xml']=serialize(root);parts['word/_rels/document.xml.rels']=serialize(relroot)
    parts['word/numbering.xml']=serialize(numbering)
    core=E.fromstring(parts['docProps/core.xml'])
    for node in list(core):
        if E.QName(node).localname in ('creator','lastModifiedBy'):node.text='TileLab Project'
        if E.QName(node).localname=='title':node.text='基于 FPGA 的瓷砖裂纹检测与证据留存系统'
    parts['docProps/core.xml']=serialize(core)
    settings=E.fromstring(parts['word/settings.xml']);u=settings.find('w:updateFields',NS)
    if u is None:u=el('w:updateFields',val='true');settings.append(u)
    else:u.set(q('w:val'),'true')
    parts['word/settings.xml']=serialize(settings)
    # Source has PNG but new screenshot is JPEG: add content type without changing originals.
    ct=E.fromstring(parts['[Content_Types].xml']);ctNS='http://schemas.openxmlformats.org/package/2006/content-types'
    if not any(x.get('Extension')=='jpg' for x in ct):
        de=E.SubElement(ct,'{'+ctNS+'}Default');de.set('Extension','jpg');de.set('ContentType','image/jpeg')
        parts['[Content_Types].xml']=serialize(ct)
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in parts.items():z.writestr(n,b)
        for n,b in images:z.writestr(n,b)
    allowed={'word/document.xml','word/_rels/document.xml.rels','word/numbering.xml','docProps/core.xml','word/settings.xml','[Content_Types].xml'}
    preserve={n:sha(parts[n]) for n in source.namelist() if n not in allowed}
    assert all(parts[n]==source.read(n) for n in preserve)
    original_numbering=E.fromstring(source.read('word/numbering.xml'))
    for a in original_numbering:
        attr='abstractNumId' if E.QName(a).localname=='abstractNum' else 'numId'
        b=numbering.find('w:'+E.QName(a).localname+"[@w:"+attr+"='"+a.get(q('w:'+attr))+"']",NS)
        assert E.tostring(a,method='c14n')==E.tostring(b,method='c14n')
    assert E.tostring(sect)==E.tostring(E.fromstring(source.read('word/document.xml')).find('w:body/w:sectPr',NS))
    qa={'reference_sha256':sha(reference.read_bytes()),'output_sha256':sha(output.read_bytes()),'preserve_only_parts':preserve,'preserved_count':len(preserve),'limits':checks,'new_figures':len(images),'output':str(output),'source_scope':'V1.53.1 host, routed V1.52 hardware/firmware','section_geometry_unchanged':True,'visual_review_pending':True}
    (HERE/'build_audit.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(output),'bytes':output.stat().st_size,'limits':checks,'preserved_parts':len(preserve),'figures':len(images)},ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--reference',type=Path,required=True);ap.add_argument('--project',type=Path,default=HERE.parents[1]/'project/pynq_z2_tile_v1_53');ap.add_argument('--output',type=Path,default=HERE.parent/'TileLab_比赛技术报告_模板版.docx');a=ap.parse_args();build(a.reference,a.project,a.output)
