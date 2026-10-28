from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from copy import copy,deepcopy
from lxml import etree as E
import hashlib,json,shutil,html
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020');work=W/'v203_materials01';work.mkdir(exist_ok=True)
base=R/'engineering_delivery_20261027/TileLab_Engineering_V202/report/TileLab_比赛技术报告.docx';assert hashlib.sha256(base.read_bytes()).hexdigest()=='6e82df4b3ea2c54e7088fe64593326bc8173eb6e641f2fca5843756f929ac58a'
target=work/'TileLab_比赛技术报告_V203.docx';assert not target.exists()
shutil.copy2(W/'v198_report01/artifact.md',work/'artifact.md');shutil.copy2(W/'v198_report01/render_word_readonly.ps1',work/'render_word_readonly.ps1')
z=ZipFile(base);parts={i.filename:z.read(i.filename) for i in z.infolist() if not i.is_dir()};ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};tag=lambda n:'{'+ns['w']+'}'+n
root=E.fromstring(parts['word/document.xml']);body=root.find('w:body',ns);paras=body.findall('w:p',ns);tables=body.findall('w:tbl',ns);assert len(paras)==81
def replace(p,text):
    rp=p.find('w:r/w:rPr',ns);rp=deepcopy(rp) if rp is not None else E.Element(tag('rPr'))
    for c in list(p):
        if c.tag!=tag('pPr'):p.remove(c)
    r=E.SubElement(p,tag('r'));r.append(rp);E.SubElement(r,tag('t')).text=text
text={
1:'面向固定花色单片瓷砖的硬件筛查与可追溯复检原型',
3:'本作品面向固定花色单片瓷砖的离线复检需求，研制基于PYNQ Z2的停驻式检测原型。针对Zynq 7020计算与片上存储资源有限的问题，将原图尺度变换、定点归一化、MobileNetV2特征提取、低维投影、良品参照距离及异常区域输出完整组织为PL整数计算链路；通过行缓存、局部累加和计算单元复用控制资源开销。PS负责传输校验与任务控制，电脑负责解码、显示和流程管理。系统按已部署参照核验输入条件，再完成检测、复核、逻辑处置与记录导出。117张公开实拍开发图的分数和掩膜与存档逐值一致，内核均时124.7毫秒，传图加检测均时501.8毫秒；100个完整逻辑周期通过。作品提供可独立核验的硬件计算模块及追溯流程，当前验证方式为照片回放。未知花色准确率、实物成像、机械动作及长期稳定性仍需后续工位验证。',
6:'使用者选择对应花色的已部署参照，完成工位核验后固定当前输入，由FPGA输出异常判定与提示区域，再记录复核及处置结论。系统为重复检查提供统一的输出和留档方式，并阻止旧结果或冲突结论被用于良品放行。现阶段每张图仍需复核，使用价值是辅助定位和规范追溯；未量化人工成本或产能收益。',
8:'目标场景是固定拍摄位置、固定光照及参照经过验证的单片瓷砖离线复检或低节拍筛查工位。采用停驻流程可先稳定输入，再完成检测与结果确认；是否符合实际节拍须结合现场取放和复核时间评估。当前公开实拍回放验证计算与流程模块，为接入固定相机、定位反馈和执行器提供原型基础。未知彩绘和多材质应按花色另建参照并独立验证。',
10:'本作品将47步任务图映射到复用的PL计算通路，内部输入224×224、输出28×28异常网格并映射至原图。卷积权重和激活采用INT8，累加采用INT32，投影和距离使用所需的更宽整数位宽。标准卷积、深度卷积与逐点卷积共用受控执行资源，行缓存和局部累加减少重复DDR访问。定点化与数据布局均按冻结参考核对；电脑只渲染PL掩膜。',
14:'（1）完整PL整数视觉链路。将特征提取与良品参照判定共同落到受限器件上，运行时无需外置GPU执行视觉推理。',
15:'（2）资源与参数复用。以任务图组织卷积、投影与距离计算；已部署参照可切换且不重下载BIT，不同花色仍需独立建参照。',
16:'（3）可追溯处置。绑定材质、参照、输入与结果，处置前复核身份，冲突和过期结果不能生成良品放行指令。',
18:'设计从器件预算与任务划分开始，确定整数算术和DDR布局，完成HLS执行单元、接口与时钟复位集成。先对齐参考与板端输出，再验证参照核验、复核处置和故障联锁。验证分别记录计算核、传图检测及完整逻辑周期，避免用单一耗时代表全部流程。',
22:'系统由电脑工作站、PS裸机传输控制、DDR和PL检测器组成。电脑解码原图并打包RGB；PS校验数据后设置输入尺寸和地址；PL自行读取原图并完成视觉计算，结果经校验返回电脑显示。此划分把视觉运算集中在可复用硬件数据通路中，便于后续接入固定工位；当前尚无同口径CPU或GPU性能、功耗对照，不据此宣称倍数加速或低功耗优势。',
23:'部署时网络和参照参数已固定，运行时由PL完成判定，电脑维护材质、核验批次、复核记录及处置。所有结果均需复核，原开发样例也不能跳过。相机和机械反馈属于后续接入项，照片回放是当前输入验证方式；框图中PC、PS和PL的职责对应实际实现。',
28:'平台为PYNQ Z2的xc7z020clg400 1。检测核心、AXI及复位同步使用PS的FCLK_CLK0，运行频率100MHz。PL包括整数检测器、存储互连、身份与复位逻辑，并保留既有HDMI采集调度通路。当前验收以网口停驻原图输入为主，保留视频接口不代表连续视频端到端吞吐已经验收。',
29:'硬件先把原图转换至内部224×224，再执行定点归一化及特征计算。RGB首层卷积、深度卷积、1×1逐点卷积、残差和融合由任务图顺序组织，完成47步后输出有效结果。相比逐层完全展开，复用执行单元控制资源占用；代价是多阶段执行及DDR访问等待，这也是本设计需要在延迟与容量之间取舍的原因。',
33:'硬件计算核由C++经Vitis HLS生成RTL，与AXI、复位和约束一起完成综合布局布线，并实际下载到PL运行。作品的自主贡献包括定点算术与数据布局、任务图和执行单元组织、投影与参照距离硬件、结果接口及验证流程；不将开发板已有PCB、公开模型或厂商接口IP作为原创。',
34:'模型、RGB原图、工作区和结果按独立DDR区域分配。行缓存保留卷积窗口数据，局部累加在输出写回前复用中间值，内部128位打包组织数据搬运。片上存储和DSP余量有限，计算阶段与参数采用复用方式。上述机制解释设计如何在器件内运行，具体效率以整机资源与实测耗时报告，不将资源接近满载视为效率证明。',
35:'算法基础来自公开的MobileNetV2预训练特征和近邻异常检测思想[1][2]。本作品根据硬件约束完成简化的整数投影与参照距离实现，不宣称发明这些算法，也不等同于原论文模型。低分辨率异常网格用于区域提示，不能视为精确裂纹轮廓；预训练特征及其派生参数遵循对应许可。',
38:'工作站提供参照选择、图片输入、结果显示和处置留档。NumPy与Pillow仅用于解码、像素打包及显示；裸机PS执行网络、CRC和任务控制，运行时没有CPU或GPU视觉推理。离线参照拟合与运行时检测分开。固定花色参照的加载属于参数配置，不会自动学习新花色。',
41:'工位核验至少使用3张不同良品和1张已知缺陷，全部一致后才可封存本批资格。这是检查已部署参照的适用性，不是训练或统计准确率认证。每次检测后，PL和复核均正常且资格有效时才可确认放行；冲突、参照变更或证据损坏会撤销资格。会话及结果编号用于拦截过期操作。',
47:'当前样机由电脑、PYNQ Z2、USB线和网线组成，输入来自公开实拍照片回放。视觉计算已在实际PL完成，整机未接入相机、光源与执行器。下列实拍位置用于展示真实开发板、接口及连线，评委可结合图1和演示视频核对计算分工。',
50:'工位接入分两层推进：检测模块输出异常判定、提示区域及对应记录；外部控制层负责到位、静止和执行完成反馈。当前已完成前者及逻辑处置流程。后续接入相机需验证成像条件和数据接口，接入分选机构需加入反馈与独立故障停机通路；本版没有声称完成这些物理动作。',
52:'实现结果为LUT42 482、寄存器60 203、BRAM127.5个36Kb等效块、DSP218/220；100MHz布局布线建立余量+0.013ns，保持余量+0.024ns，DRC错误0。资源结果表明该完整链路可装入器件，也说明后续扩展余量很小。下表与耗时数据共同描述约束，不据此单独宣称资源效率领先。',
54:'下列画面展示实际FPGA执行后的正常纹理与裂纹区域提示。输入来自MVTec AD tile公开实拍开发集，右图叠加的是PL返回掩膜。使用者可查看原图、异常区域和复核记录；区域提示辅助复检，当前没有实验证明已降低人工成本。',
55:'截图回放由脚本依据公开标签模拟复核，验证的是接口与处置流程；真实操作者可通过相同界面记录意见。样例不是独立盲测，图片结果、流程正确性和未来实物检验效果应分别评价。',
61:'验证分为三类：原图板端分数与掩膜的逐值复现；公开开发图上的图像级判定统计；标定、复核和处置的逻辑流程测试。网络、参照和阈值均先冻结，标签仅由验收脚本在板端返回后用于评价或模拟复核，不输入PL检测请求。',
62:'117张公开开发图中，33张正常图未报警、84张缺陷图检出；全部分数和掩膜与存档逐值一致。这证明冻结部署在该开发集上的行为和数值一致性，尚不能外推未知花色、独立实物批次或像素级分割精度。实际部署必须另留独立验证集，按花色报告误报与漏检。',
63:'两套已部署参照可不更换BIT切换：纹理砖为主验证场景，陶瓦为公开照片迁移实验，不代表彩绘地砖验收。3良品加1缺陷核验不生成新模型。为避免只保留成功结果，跨材质误报、候选阈值漏检及POR失败均保存在随附记录，正式结论按实际数据范围给出。',
64:'117图的内核均时124.72ms、传图加检测均时501.79ms；两者相差还包含网络及协议处理，不可全部归为单一拷贝开销。100完整周期均时1.220s，含0.25s脚本复核等待、API及落盘，不含真实人员与机械等待。201次固定图连续计算是内核微基准，不能换算为新视频帧率或产线产能。',
65:'在此前同一32次原图对照中，传输优化使传图加检测均时由0.54084s降至0.49865s，约7.8%，输出保持一致；该对照对应V199传输优化，不是CNN算法加速，亦非CPU对FPGA加速比。本轮换线后的完整试验约310秒，同一启动编号且结束未记录新复位原因位。证据详见reports/v199与reports/v202。',
70:'落地优先补齐固定成像、工件定位和独立批次验证，再按工位节拍决定执行机构及接口。应评估各花色误报漏检、不同光照与位置变化、长时间稳定性及人工复核耗时。功耗、成本和与软件方案的收益需实测后报告；多砖墙面与新模型作为后续独立任务。',
72:'本项目的主要收获是把算法原理转成可验证的硬件实现和可使用的处置流程。器件预算决定计算复用与数据搬运方式；冻结算术、模型和接口后，数值比对、实现时序与上板结果分别验证不同问题。对使用者而言，参数对应当前花色、结果对应当前输入，以及异常时不沿用旧结论，同样影响系统是否可信。',
73:'设计中否决了单张约94.6秒的HFENet硬件候选，恢复轻量参照检测链路；两者模型和输入条件不同，不能直接比较准确率。此前100MHz及50MHz候选均出现过POR，50MHz未通过整轮复测。换线后100MHz通过有限测试，电气根因及长期稳定性仍待进一步确认。',
74:'当前成果定位为固定条件下的单片瓷砖硬件筛查与可追溯复检原型。完整PL视觉计算、已部署参照切换及逻辑处置可复现；相机成像和机械联动有明确接入方向，但尚未在现场验证。后续应以独立实物证据检验应用收益。'
}
for i,t in text.items():replace(paras[i],t)
# Add a compact provenance matrix using the retained table formatting.
matrix=deepcopy(tables[1]);matrix_rows=matrix.findall('w:tr',ns)
for row in matrix_rows[1:]:matrix.remove(row)
content=[['已有基础','本作品完成','验证依据'],['公开预训练特征与异常检测思想','整数算术、任务图、投影及参照距离的PL实现','47步整图运行及117图数值核对'],['AMD及第三方接口IP','计算核集成、DDR布局、控制及结果接口','实现时序和匹配BIT XSA ELF'],['已冻结模型与参照参数','已部署参照切换、资格与结果绑定、复核留档','22次闭环回放与38次拦截']]
for index,row in enumerate(content):
    tr=matrix_rows[0] if index==0 else deepcopy(matrix_rows[1])
    if index:matrix.append(tr)
    for cell,value in zip(tr.findall('w:tc',ns),row):replace(cell.find('w:p',ns),value)
paras[16].addnext(matrix)
parts['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(target,'w',ZIP_DEFLATED) as out:
    for item in z.infolist():
        if not item.is_dir():out.writestr(copy(item),parts[item.filename])
with ZipFile(target) as final:
    assert final.testzip() is None
    for n in z.namelist():
        if n!='word/document.xml' and not n.endswith('/'):assert final.read(n)==z.read(n),n
proof=dict(output=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),baseline_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),only_changed_package_part='word/document.xml',unchanged_detector=True,claim_source='V202 hardware acceptance and V199 matched transport comparison')
(work/'build_proof.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof))
