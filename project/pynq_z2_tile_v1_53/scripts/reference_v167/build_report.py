"""Build the design report from completed board and algorithm evidence only."""
from pathlib import Path
import argparse,json,re,statistics,hashlib
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
R=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--bundle',required=True,type=Path);p.add_argument('--algorithm',required=True,type=Path,nargs='+');p.add_argument('--performance',type=Path);p.add_argument('--baseline',type=Path,nargs='*',default=[]);p.add_argument('--out',required=True,type=Path);p.add_argument('--font',type=Path,default=Path('C:/Windows/Fonts/simhei.ttf'));a=p.parse_args()
    board=json.loads(a.board.read_text(encoding='utf8'));manifest=json.loads((a.bundle/'DEPLOYMENT.json').read_text());algorithms=[json.loads(f.read_text()) for f in a.algorithm]
    if not board.get('passed') or not board.get('rows'):raise ValueError('Complete board replay required before report generation')
    if board.get('programming',{}).get('deployment_sha256')!=hashlib.sha256((a.bundle/'DEPLOYMENT.json').read_bytes()).hexdigest():raise ValueError('Board evidence belongs to a different deployment')
    pdfmetrics.registerFont(TTFont('Chinese',str(a.font)));styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='BodyCN',fontName='Chinese',fontSize=10,leading=16,spaceAfter=9));styles.add(ParagraphStyle(name='TitleCN',fontName='Chinese',fontSize=27,leading=36,textColor=colors.HexColor('#183d50'),spaceAfter=18));styles.add(ParagraphStyle(name='HeadCN',fontName='Chinese',fontSize=16,leading=23,textColor=colors.HexColor('#087c89'),spaceBefore=15,spaceAfter=10,keepWithNext=True));styles.add(ParagraphStyle(name='SmallCN',fontName='Chinese',fontSize=8,leading=12,spaceAfter=5));styles.add(ParagraphStyle(name='CellCN',fontName='Chinese',fontSize=8.5,leading=12))
    story=[]
    def para(text,style='BodyCN'):return Paragraph(escape(str(text)).replace('\n','<br/>'),styles[style])
    def add(text,style='BodyCN'):story.append(para(text,style))
    def head(text):add(text,'HeadCN')
    def table(rows,widths):
        t=Table([[para(c,'CellCN') for c in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e1eff2')),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#b9ccd3')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.append(t);story.append(Spacer(1,9))
    def page(c,doc):
        c.setStrokeColor(colors.HexColor('#b9ccd3'));c.line(42,40,553,40);c.setFont('Chinese',8);c.setFillColor(colors.HexColor('#506b78'));c.drawString(42,27,'TileLab | 单片良品参照检测 | V1.67');c.drawRightString(553,27,str(doc.page))
    add('TileLab\n单片瓷砖良品参照检测系统','TitleCN');add('PYNQ-Z2 / Zynq-7020 / Vivado与Vitis 2025.2');add('完整图像差分硬件、按花色标定、可追溯检测与异常拒判');story.append(Spacer(1,18))
    table([['交付范围','本报告采用的证据'],['输入','固定1280×720 HDMI；单片表面ROI为[390,110]至[889,609]，完整500×500像素'],['分工','电脑配准、光照估计及区域分析；FPGA执行全幅归一化与差分；ARM负责DDR和网络'],['实测','实际开发板HDMI回放与完整差异图核对，程序生成花纹与人工缺陷单独标识'],['准确率边界','未完成独立实体瓷砖、相机与光学成像验证；无报警不等于良品认证']], [78,433])
    add('本报告按实际实现与原始记录生成。国奖评定由赛事评委决定；本文不把程序生成样本、开发集、仿真或回放结果写成工业准确率认证。','SmallCN');story.append(PageBreak())
    head('1. 应用目标与设计取舍')
    add('彩绘图案、木纹和釉面变化会使仅依赖暗线或边缘的检测器产生误报。本设计在固定拍摄位置与光照下，按花色保存一张完整良品参照，将检测任务限定为同一空间花纹相对参照的表面变化。不同自然纹理即使属于同类材质，也不能直接互作良品参照。')
    add('项目没有新训练分类模型。关键取舍是将花纹身份、位置与光照一致性先行校验，再以保留单像素亮度细节的定点差分发现变化。系统输出变化候选，不能自动区分裂纹、污渍、印刷变化和釉面损伤。')
    head('2. 系统架构与完整数据流')
    diagram=Drawing(511,110)
    for x,label,detail in [(0,'视频源','HDMI 720p60'),(173,'PL / ARM','采集 + DDR + 全图差分'),(346,'电脑工作站','标定 + 配准 + 区域分析')]:
        diagram.add(Rect(x,28,165,65,fillColor=colors.HexColor('#e1eff2'),strokeColor=colors.HexColor('#087c89')));diagram.add(String(x+82.5,69,label,fontName='Chinese',fontSize=12,textAnchor='middle'));diagram.add(String(x+82.5,46,detail,fontName='Chinese',fontSize=9,textAnchor='middle'))
    for x in (165,338):
        diagram.add(Line(x,60,x+8,60,strokeColor=colors.HexColor('#087c89')));diagram.add(Polygon([x+8,60,x+4,63,x+4,57],fillColor=colors.HexColor('#087c89')))
    diagram.add(String(255,10,'电脑准备配对数据 -> ARM提交PL计算 -> 差异图返回电脑',fontName='Chinese',fontSize=9,textAnchor='middle'));story.append(diagram)
    table([['环节','实现与边界'],['采集','PC或其他视频源 HDMI -> PL接收与格式计数 -> AXI异步FIFO -> SG DMA -> DDR；每帧CRC与元数据绑定'],['标定','保存实际捕获的720p良品、花色ID、算法和策略哈希；不可覆盖旧标定版本'],['准备','电脑使用四条物理边界确定双轴位移，再校验内部花纹；估计RGB增益和偏移，生成配对图像'],['计算','ARM校验上传数据与参数，刷新缓存并启动AXI DDR加速器；PL输出250000个分数与强/弱标志'],['判断','电脑核对版本、请求身份和输出CRC，再筛选连通区域、补全已确认候选并保存结果'],['异常','错花色、位姿超限、光照越界、数据错误和超时均不输出“良品通过”']], [70,441])
    add('当前版本是电脑与FPGA协同系统。配准和连通区域分析尚未迁移到ARM，不能把本版本描述为完全脱离电脑的自主检测设备。视频输入帧率、计算核耗时与完整检测吞吐分别测量。')
    head('3. 配准、标定与缺陷判定')
    add('配准分别使用两条竖边与两条横边的背景混合轮廓，搜索整数位移并细化到1/16像素。条纹缺少某一方向纹理时，外边界仍提供该轴位置约束。随后检查内部花纹相关性和局部漂移；错误参照不会仅因轮廓相似而被接受。')
    add('光照估计按良品强度分层取条件中位数，优先选取参照中的平坦区域，避免把JPEG彩色边缘混合拟合成全局曝光变化。无法可靠确定增益时只估计偏移。估计参数使用8像素内缩采样；实际差分仍检查全部500×500像素，没有裁去表面边缘。')
    add('RGB归一化：N = clip(((C × gain_q8 + 128) >> 8) + offset, 0, 255)。亮度Y=(R+2G+B+2)>>2；色度Co=(R-B+256)>>1、Cg=(-R+2G-B+512)>>2。只对色度取3×3整数均值，亮度保留原生细节。')
    add('差异分数取亮度差、两路平均色度差、以及扣除良品5×5色度范围后的原生色度差之最大值。强/弱阈值为18/9，并加入由良品计算的边缘容差。ROI边界复制参与计算，所有250000个声明像素均有输出。')
    add('先用保守强/弱连接规则确认候选，再允许超过原始高阈值18的相连像素补回边缘间隙，并保留原已确认像素。补全过程只由已通过的候选掩码播种，因而不会把原先无候选图变成新的图片级报警。早期采用低阈值补全导致像素误检扩张，已弃用；像素精确率与覆盖率同时报告。')
    head('4. FPGA实现与缓冲区所有权')
    add('加速器通过AXI主接口读取配对RGB与容差，内部使用行缓存和5×5窗口，在流水线上计算Q8归一化、色度均值、局部范围与严格阈值比较。AXI-Lite负责控制。高、低阈值求和使用足够位宽，避免8位溢出。')
    add('网络上传、FPGA计算及结果发送拥有明确状态。连接中断不等于DDR计算完成；在ap_done确认之前不能复用仍由硬件访问的输入和输出缓冲区。传输使用复制发送，避免网卡保留旧缓冲引用。原始采集先落盘并同步，之后才确认事件。')
    status=dict(line.split('=',1) for line in (a.bundle/'implementation_status.txt').read_text().splitlines() if '=' in line);util=(a.bundle/'utilization.rpt').read_text()
    def used(name):
        m=re.search(r'\|\s*'+re.escape(name)+r'\s*\|\s*([\d.]+)',util);return m[1] if m else '见原始报告'
    table([['整机实现指标','数值'],['器件 / 主时钟','xc7z020clg400-1 / 100 MHz'],['建立 / 保持余量',status['setup_slack_ns']+' ns / '+status['hold_slack_ns']+' ns'],['DRC错误',status['drc_errors']],['LUT / 寄存器',used('Slice LUTs')+' / '+used('Slice Registers')],['BRAM36等效 / DSP',used('Block RAM Tile')+' / '+used('DSPs')]], [175,336])
    add('以上为包含HDMI、采集和完整图像差分模块的整机实现结果。HLS估算与旧独立算术BIST的资源和频率不替代此表。详细时序、总线偏斜、CDC、布线和利用率报告随工程提供。')
    head('5. 验证层级与原始记录')
    table([['层级','已完成内容','不能据此声称'],['C与RTL','两幅完整图、500000个像素精确核对；包含边界、Q8补偿和饱和','真实瓷砖准确率'],['固件与协议','分段上传、CRC、参数边界、断线所有权和超时路径；请求身份和整图重建','物理链路必然无故障'],['实际开发板','HDMI采集、DDR、网络和PL全幅差异图；每个返回像素对照独立NumPy参考','相机光学和工厂泛化'],['算法数据','已有开发用例与新增程序花纹分组保留全部失败，拒判单列','独立实体瓷砖统计结论']], [72,250,189])
    head('6. 算法结果与失败分析')
    for alg,path in zip(algorithms,a.algorithm):
        add(path.parent.name+' / '+alg['scope'],'SmallCN')
        rows=[['组别','数量','报警','拒判','图片预期通过']]
        for name,g in alg['groups'].items():rows.append([name,g['n'],g.get('alarms',g.get('alarm',0)),g['rejected'],g['passed']])
        table(rows,[195,55,70,70,121])
        failed=[r['id'] for r in alg['rows'] if not r['passed']];add('失败保留：'+('、'.join(failed) if failed else '本组图片级预期均通过')+'。','SmallCN')
        positive=[r for r in alg['rows'] if r.get('coverage') is not None];tp=sum(r.get('tp',0) for r in positive);pred=sum(r.get('predicted_pixels',0) for r in positive);gt=sum(r.get('gt_pixels',0) for r in positive)
        if gt:add(f'完整正样本分母的像素覆盖率 {tp/gt:.2%}；像素精确率 {tp/pred:.2%}；拒判和漏检的GT仍计入分母。' if pred else '本组没有有效像素候选。','SmallCN')
    add('弱到低于成像、压缩和纹理残差的单像素变化仍可能漏检。不得删除这些用例后宣称100%识别。固定花纹、光照与位置是本方案的使用条件；自然纹理跨瓷砖的随机变化可能导致拒判。')
    head('7. 实板回放与端到端耗时')
    inspected=[r for r in board['rows'] if r['source']['kind']!='reference'];scored=[r for r in inspected if r['result'].get('hardware')];mismatches=sum(r.get('score_mismatch_pixels',0) for r in inspected)
    table([['实测项','结果'],['采集图片 / 检测操作',f"{len(board['rows'])} / {len(inspected)}"],['实际PL差异图数',str(len(scored))],['逐像素不一致',str(mismatches)],['图片级预期',str(sum(r.get('expectation_passed',False) for r in inspected))+'/'+str(len(inspected))],['独立实体瓷砖试件','0；本回放为程序生成图像经真实HDMI链路输入']], [175,336])
    if scored:
        engines=[r['result']['hardware']['engine_seconds']*1000 for r in scored];network=[r['result']['hardware']['request_seconds']*1000 for r in scored];total=[r['seconds']*1000 for r in inspected]
        table([['耗时口径','中位数 / 最大值'],['实际FPGA计算',f'{statistics.median(engines):.3f} / {max(engines):.3f} ms'],['上传、计算与结果返回',f'{statistics.median(network):.3f} / {max(network):.3f} ms'],['完整检测操作',f'{statistics.median(total):.3f} / {max(total):.3f} ms']], [175,336])
    if a.performance:
        performance=json.loads(a.performance.read_text())
        if performance['board_sha256']!=hashlib.sha256(a.board.read_bytes()).hexdigest():raise ValueError('Performance evidence belongs to different board captures')
        table([['同一组12幅实际捕获图的差分算子','中位耗时'],['NumPy完整图参考（不含配准）',f"{performance['cpu_median_ms']:.3f} ms"],['实际PL完整图算子',f"{performance['pl_median_ms']:.3f} ms"],['含采集/配准/网络/区域分析的完整比对',f"{performance['full_median_ms']:.3f} ms"]],[335,176])
        add('上表完整比对统计12次实际进入PL的检测；前表完整操作包含6次拒判。CPU与PL只比较相同差分算子，未声称整机相对CPU的同倍数加速。','SmallCN')
    if a.baseline:
        rows=[['固件优化阶段（实际开发板）','请求中位耗时']]
        names=['逐字节CRC / TCP窗口2048','查表CRC / TCP窗口2048','查表CRC / TCP窗口65535']
        for name,path in zip(names,a.baseline):
            data=json.loads(path.read_text());samples=[r['result']['hardware']['request_seconds']*1000 for r in data['rows'] if r['result'].get('hardware')];rows.append([name,f'{statistics.median(samples):.3f} ms'])
        rows.append(['当前最终算法与完整新平台',f'{statistics.median(network):.3f} ms']);table(rows,[335,176])
        add('每次请求上传2MB配对图并返回1MB差异图。各阶段使用同一PL实现，比特流及PL资源不变；变化在ARM CRC与TCP配置，PL资源增量为0，ARM则增加查表及网络缓冲占用。主机算法与运行负载并非全部相同，故此表仅说明传输阶段优化，不能用其推导完整算法速度或准确率增益。原始阶段汇总随包保留。','SmallCN')
    for kind,title in [('good','正常表面'),('line','人工线缺陷'),('invalid_pose','位姿超限拒判')]:
        row=next((r for r in inspected if r['source']['kind']==kind),None)
        if row:
            preview=Path(row['result']['preview'])
            if preview.exists():
                im=Image(str(preview));scale=min(360/im.imageWidth,180/im.imageHeight);im.drawWidth=im.imageWidth*scale;im.drawHeight=im.imageHeight*scale
                story.append(KeepTogether([para(title+' / '+row['source']['source'],'SmallCN'),im,Spacer(1,12)]))
    head('8. 从零复现与操作步骤')
    add('安装Python及NumPy、Pillow；安装Vivado/Vitis 2025.2和板卡驱动。完整构建顺序为HLS C/RTL验证、独立Vivado工程、匹配XSA/BIT与ARM固件、封存部署清单。工程README提供所有命令及新输出目录参数。')
    add('使用JTAG易失性下载脚本前关闭工作站；脚本校验文件哈希、时序及XSA内嵌比特流，下载后检查固件、PL和ROI身份。PS参考时钟先于HDMI热插拔使能启动，无需外接HDMI OUT显示器。')
    add('电脑HDMI接开发板HDMI IN，网线接以太网，输入设为1280×720、60 Hz。启动reference_station.py，确认完整良品与固定暗背景后按花色编号标定。更换花色须切换对应标定；检测、拒判与原始证据保存在独立记录目录。')
    head('9. 可复用经验、协作记录与提交边界')
    add('skill目录提供通用数组精确比对、部署文件校验与DMA所有权排查工作流。它们从本项目的实际失败提炼，可用于其他定点信号处理任务；硬件来源、黄金参考与场景标注仍需独立确认。evidence中的协作记录保留提示词摘要、工具结果、自我纠错和失败轨迹。')
    add('当前可以证明工程链路及指定回放数据上的行为。高准确率实体瓷砖验收仍需要同一花色的独立良品和真实裂纹试件，固定成像位置和光照，并将漏检、误报和拒判分别统计。此前提出的100正样本/400负样本及置信区间目标属于工程目标，不是已核实的官方比赛门槛。')
    add('部署清单SHA256：'+hashlib.sha256((a.bundle/'DEPLOYMENT.json').read_bytes()).hexdigest(),'SmallCN');add('实板记录SHA256：'+hashlib.sha256(a.board.read_bytes()).hexdigest(),'SmallCN')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.out.exists():raise FileExistsError('Choose a new report output path')
    SimpleDocTemplate(str(a.out),pagesize=(595,842),leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=54,title='TileLab single-tile reference design report',author='TileLab').build(story,onFirstPage=page,onLaterPages=page)
    print(a.out)
if __name__=='__main__':main()
