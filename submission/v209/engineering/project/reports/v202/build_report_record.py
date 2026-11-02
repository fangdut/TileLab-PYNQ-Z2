from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from copy import copy,deepcopy
from lxml import etree as E
from PIL import Image,ImageDraw,ImageFont
import hashlib,json,shutil,io
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020');work=W/'v202_report01';work.mkdir(exist_ok=True)
baseline=R/'engineering_delivery_20261027/TileLab_Engineering_V200/report/TileLab_比赛技术报告.docx';source=W/'v202_usb_retest01';s=json.loads((source/'summary.json').read_text());assert s['passed']
q=s['exact117'];f=s['soak100'];a=s['workflow22'];assert q['cases']==117 and f['completed_cycles']==100 and f['passed'] and a['controls_rejected']==38
assert hashlib.sha256(baseline.read_bytes()).hexdigest()=='f434ec676e5a91de7e5eacdc30200021c534a4ac8589d989b01c2198b4f07a19'
target=work/'TileLab_比赛技术报告_V202.docx';assert not target.exists()
shutil.copy2(W/'v198_report01/artifact.md',work/'artifact.md');shutil.copy2(W/'v198_report01/render_word_readonly.ps1',work/'render_word_readonly.ps1')
z=ZipFile(baseline);parts={i.filename:z.read(i.filename) for i in z.infolist() if not i.is_dir()};ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};tag=lambda x:'{'+ns['w']+'}'+x
root=E.fromstring(parts['word/document.xml']);paras=root.find('w:body',ns).findall('w:p',ns);tables=root.find('w:body',ns).findall('w:tbl',ns);assert len(paras)==81 and len(tables)==5
def replace(p,text):
    rp=p.find('w:r/w:rPr',ns);rp=deepcopy(rp) if rp is not None else E.Element(tag('rPr'))
    for child in list(p):
        if child.tag!=tag('pPr'):p.remove(child)
    run=E.SubElement(p,tag('r'));run.append(rp);t=E.SubElement(run,tag('t'));t.text=text
def cell(table,row,col,text):
    c=tables[table].findall('w:tr',ns)[row].findall('w:tc',ns)[col];p=c.find('w:p',ns);replace(p,text)
engine=q['mean_engine_seconds']*1000;wall=q['mean_transfer_detection_seconds']*1000;cycle=f['cycle_seconds']['mean']
text={
1:'PYNQ Z2 良品参照核验与硬件检测闭环',
3:f'本作品面向固定输入条件下的瓷砖表面缺陷检查，构建材质参照核验、固定输入、FPGA检测、复核及确认处置的停驻式样机。PYNQ Z2的可编程逻辑完成原图尺度变换、定点归一化、MobileNetV2特征提取、低维投影、良品特征库距离计算、图像级判定及异常区域输出。ARM负责网络、完整性校验与任务控制，电脑负责解码、显示和流程管理，运行时不执行视觉推理。100MHz基线在用户更换USB线后完成117张公开实拍开发图逐值复现，内核均时{engine:.1f}毫秒，传图加检测均时{wall:.1f}毫秒；随后100个完整闭环周期通过。复核由公开标签驱动的脚本模拟，不是实物或真实人工验收。既有HDMI流水线保留，当前以网口原图停驻检测为主；无机械执行器，未验收任意彩绘和未知材质。',
6:'系统接收未经电脑缩放或修补的PNG、JPEG原图。操作员建立材质记录并选择已部署参照，至少用3张不同良品和1张已知缺陷核验一致后封存本批资格。每次PL检测后都须记录复核结论，再确认放行或隔离。冲突会撤销资格；断连、启动变化或证据异常时清除可处置结果。新材质不能靠登记名称自动学会，需另建并验证参照。',
12:'网口停驻流程。内核和传图指标来自117张原图；完整周期另包含脚本复核等待。',
16:'（3）将材质、参照、标定批次、启动、输入及结果绑定；处置前重新核验身份，复核冲突和旧结果复用不能生成良品放行。',
18:'先建立定点参考、任务图和良品参照，再完成C与RTL核对、综合及时序检查，生成匹配BIT、XSA和ELF。上板核对原图分数与掩膜，随后验证参照核验、检测、复核、处置及故障联锁。最后冻结工程与追溯记录。',
23:'PL决定异常分数及掩膜。电脑维护材质、参照指纹、标定批次与操作记录；标定资格只表示本批参照核验完成。所有检测结果均经过复核步骤，原有开发样例也不能跳过。JSON和CSV记录原图及模型指纹、帧序号、复核人员和处置。',
28:'采用PYNQ Z2上的Zynq 7000器件xc7z020clg400 1。检测核心、AXI及复位同步均由PS的FCLK_CLK0驱动，运行基线为100MHz；没有用外部PL引脚提供检测时钟。HDMI像素时钟属于独立通路。PS连接以太网、DDR及调试接口，PL保留整数检测器、AXI、身份寄存器、复位及视频采集调度逻辑。',
41:'控制器用会话、修订和结果编号拒绝过期操作。标定至少需要3张不同良品和1张已知缺陷，冻结后才能生产检测。每次结果先进入待复核；仅PL与复核均正常且资格有效时允许确认放行。冲突、板端参照变化或证据损坏会撤销资格并阻止放行。重启不恢复旧工件。',
44:'图2 标定核验与单次检测处置流程',
54:'工作站已实现材质登记、参照切换、核验封存、真实图片输入、PL检测、复核与审计导出。下列图像来自换线后100MHz实板自动回放，左右分别为MVTec AD tile实拍与FPGA粗粒度异常区域叠加。它们不是生成的瓷砖照片，也不是电脑重新推理。',
55:'截图回放的复核由脚本依据公开标签模拟，不代表真实人工验收。性能表记录整轮复测，截图不代替平均统计。两张截图与117图及100周期测试属于同一启动编号。',
61:'模型及阈值在测试前冻结，运行中未根据测试标签修改。板端先返回检测结果，独立验收脚本再使用公开标签模拟复核并检查流程；标签不传给PL检测器。原图、模型、BIT、ELF及结果摘要随记录保留。该流程测试不是独立准确率试验。',
63:'本版未完成任意彩绘、多材质或真实相机产线验收。纹理砖参照与实验陶瓦参照可选择切换；登记新名称不生成新模型。已有跨材质良品误报及候选阈值漏检记录保留。具体花色仍需良品参照、冻结协议及独立工件组验证，不能用同一批开发照片推广。',
64:f'本轮换线后，117图、连续固定图计算、22次闭环回放及100个完整周期均在同一启动编号下完成。117图无额外间隔且没有连接建立重试。100周期平均{cycle:.3f}秒，包括0.25秒脚本复核等待、API与证据落盘；不含真实人工和机械等待。末次检查未记录新复位原因位。这是本轮有限测试通过，不能称为长期连续无故障。',
65:'V202原始证据见project/reports/v202。模型SHA256仍以1501e32e733b566e开头。换线是用户报告的外部条件变化，代码、BIT、ELF和模型未因此改变。重复开发集高判对率不代表独立批次准确率；本轮对照也没有测量电压或电流。',
70:'后续优先完成固定相机、光源、定位反馈及独立批次实物验证，按花色建立参照并冻结阈值。继续评估供电与POR路径，扩大长时间稳定性测试。硬件可研究DDR突发访问、位宽及资源复用；多砖墙面另行解决砖体定位、砖缝和尺度变化。',
74:'此前100MHz完整流程和50MHz候选均复现过POR复位，CPU回到启动ROM、DDR进入复位。50MHz虽通过100周期，后续117图仅完成97张，因此未替换交付版。更换USB线后，同一100MHz基线通过本轮完整试验；这提示连接或供电路径需进一步核验，尚不能唯一确定电气根因。失败证据全部保留，异常请求不自动重放。'
}
for i,value in text.items():replace(paras[i],value)
for row,value in [(1,'100 MHz PS FCLK_CLK0'),(5,f'{engine:.1f} ms 117张'),(6,f'{wall:.1f} ms 117张')]:cell(0,row,1,value)
rows=[['开发图像级判定','117张','33正常零误报 84缺陷检出'],['分数及原图掩膜','117张','与存档逐值一致 序号除外'],['完整闭环周期','100次','50次放行 50次隔离 脚本复核'],['非合规操作','38次','38次拒绝'],['117图内核均时','成功请求',f'{engine:.2f} ms'],['117图传图检测均时','无额外图间等待',f'{wall/1000:.3f} s'],['完整周期均时','含0.25秒脚本复核',f'{cycle:.3f} s']]
for i,row in enumerate(rows,1):
    for j,value in enumerate(row):cell(4,i,j,value)
# Replace the existing state diagram in its retained layout slot.
im=Image.new('RGB',(1600,920),'white');draw=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',32);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',25)
boxes=[(80,70,710,250,'建立材质并选择已部署参照','记录花色与拍摄条件'),(890,70,1520,250,'核验并封存本批资格','至少3张不同良品及1张已知缺陷'),(80,380,710,560,'固定输入并启动FPGA检测','保存原图指纹和板端结果'),(890,380,1520,560,'记录复核结论','绑定本次结果和复核人员')]
for x1,y1,x2,y2,title,sub in boxes:
    draw.rounded_rectangle((x1,y1,x2,y2),radius=12,outline='black',width=3);draw.text(((x1+x2)/2,y1+47),title,font=font,fill='black',anchor='mm');draw.text(((x1+x2)/2,y1+112),sub,font=small,fill='black',anchor='mm')
def arrow(points):
    draw.line(points,fill='black',width=4);x,y=points[-1];px,py=points[-2]
    if x>px:tri=[(x,y),(x-18,y-10),(x-18,y+10)]
    elif x<px:tri=[(x,y),(x+18,y-10),(x+18,y+10)]
    else:tri=[(x,y),(x-10,y-18),(x+10,y-18)]
    draw.polygon(tri,fill='black')
arrow([(710,160),(890,160)]);arrow([(1200,250),(1200,310),(395,310),(395,380)]);arrow([(710,470),(890,470)]);arrow([(1200,560),(1200,640)])
draw.rounded_rectangle((240,640,1380,800),radius=12,outline='black',width=3);draw.text((810,685),'条件一致且双方正常 → 确认放行',font=font,fill='black',anchor='mm');draw.text((810,750),'缺陷 → 隔离　冲突或异常 → 禁止放行并重新核验',font=small,fill='black',anchor='mm');draw.text((800,865),'本图为逻辑流程　未连接实体机械执行器',font=small,fill='black',anchor='mm')
diagram=work/'closed_loop.png';im.save(diagram);parts['word/media/tilelab_1002.png']=diagram.read_bytes()
for number,name in [(1003,'good.png'),(1004,'defect.png')]:parts[f'word/media/tilelab_{number}.png']=(W/'v202_report_images'/name).read_bytes()
# Preserve picture slots and width while matching each new bitmap's aspect.
wp='{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}';aa='{http://schemas.openxmlformats.org/drawingml/2006/main}';rr='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
for drawing in root.iter(wp+'inline'):
    blip=next(drawing.iter(aa+'blip'));ident=blip.get(rr+'embed')
    if ident in ['rId1002','rId1003','rId1004']:
        image=Image.open(io.BytesIO(parts['word/media/tilelab_'+ident[3:]+'.png']));extent=drawing.find(wp+'extent');cy=round(int(extent.get('cx'))*image.height/image.width);extent.set('cy',str(cy))
        for xfrm in drawing.iter(aa+'xfrm'):
            ext=xfrm.find(aa+'ext')
            if ext is not None:ext.set('cy',str(cy))
parts['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(target,'w',ZIP_DEFLATED) as archive:
    for item in z.infolist():
        if not item.is_dir():archive.writestr(copy(item),parts[item.filename])
editable={'word/document.xml','word/media/tilelab_1002.png','word/media/tilelab_1003.png','word/media/tilelab_1004.png'}
with ZipFile(target) as final:
    assert final.testzip() is None
    for name in z.namelist():
        if not name.endswith('/') and name not in editable:assert z.read(name)==final.read(name),name
save=dict(output=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),baseline_preserved_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),only_changed_parts=sorted(editable),evidence_summary_sha256=hashlib.sha256((source/'summary.json').read_bytes()).hexdigest(),template_styles_headers_numbering_sections_preserved=True)
(work/'build_proof.json').write_text(json.dumps(save,indent=2));print(json.dumps(save))
