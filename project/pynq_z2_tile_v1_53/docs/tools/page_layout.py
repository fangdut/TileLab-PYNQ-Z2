from pathlib import Path
import sys,json,html,re,copy,hashlib,datetime
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle,Spacer,Flowable,Image
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage


ROOT=Path(__file__).resolve().parents[2]; PROJECT=ROOT
OUT=ROOT/'docs';TMP=ROOT/'reports/document_qa';OUT.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('Song','C:/Windows/Fonts/simsun.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('Hei','C:/Windows/Fonts/simhei.ttf'))
pdfmetrics.registerFont(TTFont('Arial','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFontFamily('Song',normal='Song',bold='Hei',italic='Song',boldItalic='Hei')
NAVY=colors.HexColor('#143346');TEAL=colors.HexColor('#087E85');GOLD=colors.HexColor('#C8843D');INK=colors.HexColor('#253C4A');MUTED=colors.HexColor('#617685');LIGHT=colors.HexColor('#EDF5F5');RULE=colors.HexColor('#D7E2E7')
W,H=595.276,841.89;M=47;CW=W-2*M
ST={
 'body':ParagraphStyle('body',fontName='Song',fontSize=11.1,leading=17.7,textColor=INK,wordWrap='CJK',spaceAfter=8),
 'small':ParagraphStyle('small',fontName='Song',fontSize=10,leading=15.2,textColor=INK,wordWrap='CJK'),
 'h':ParagraphStyle('h',fontName='Hei',fontSize=12.2,leading=18,textColor=TEAL,spaceBefore=8,spaceAfter=5,wordWrap='CJK'),
 'lead':ParagraphStyle('lead',fontName='Song',fontSize=11,leading=17.5,textColor=MUTED,spaceAfter=12,wordWrap='CJK'),
 'th':ParagraphStyle('th',fontName='Hei',fontSize=9.3,leading=14,textColor=colors.white,wordWrap='CJK'),
 'eq':ParagraphStyle('eq',fontName='Song',fontSize=11,leading=17.5,textColor=NAVY,wordWrap='CJK'),
 'caption':ParagraphStyle('caption',fontName='Song',fontSize=9,leading=13,textColor=MUTED,spaceAfter=7,wordWrap='CJK'),
}
def para(s,style='body'):
 s=str(s).replace('\u2011','-').replace('\u2013','-').replace('\u2014','-')
 t=html.escape(s).replace('\n','<br/>')
 t=re.sub(r'https://[^<\s]+',lambda m:'<link href="'+m.group(0)+'" color="#087E85">'+m.group(0)+'</link>',t)
 # Long local paths and references may break at separators without changing text.
 return Paragraph(t,ST[style])
def tab(head,rows,width=CW):
 assert all(len(r)==len(head) for r in rows),(head,rows)
 n=len(head);ratios=([.30,.70] if n==2 else [.23,.30,.47] if n==3 else [1/n]*n)
 if n==3 and len(str(head[1]))>8:ratios=[.24,.38,.38]
 data=[[para(v,'th') for v in head]]+[[para(v,'small') for v in r] for r in rows]
 t=Table(data,colWidths=[width*x for x in ratios],hAlign='LEFT')
 cmds=[('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.5,NAVY)]
 for k in range(1,len(data)):cmds += [('BACKGROUND',(0,k),(-1,k),colors.white if k%2==0 else LIGHT),('LINEBELOW',(0,k),(-1,k),.3,RULE)]
 t.setStyle(TableStyle(cmds));return t

class Diagram(Flowable):
 def __init__(self,name):super().__init__();self.name=name;self.width=CW;self.height={'architecture':148,'algorithm':128,'clocks':150,'dma':135,'wiring':130,'valley':110,'window':110,'regions':110,'pipeline':115}.get(name,110)
 def draw(self):
  c=self.canv;ww=self.width;hh=self.height
  c.setFillColor(LIGHT);c.roundRect(0,3,ww,hh-7,8,fill=1,stroke=0)
  def line(x1,y1,x2,y2):
   c.setStrokeColor(TEAL);c.setLineWidth(1.4);c.line(x1,y1,x2,y2)
   import math
   a=math.atan2(y2-y1,x2-x1);p=c.beginPath();p.moveTo(x2,y2);p.lineTo(x2-5*math.cos(a-.4),y2-5*math.sin(a-.4));p.lineTo(x2-5*math.cos(a+.4),y2-5*math.sin(a+.4));p.close();c.setFillColor(TEAL);c.drawPath(p,fill=1,stroke=0)
  def label(x,y,s,size=9,color=INK):c.setFillColor(color);c.setFont('Hei',size);c.drawCentredString(x,y,s)
  def box(x,y,bw,bh,title,sub='',color=NAVY):
   c.setFillColor(colors.white);c.setStrokeColor(RULE);c.roundRect(x,y,bw,bh,5,fill=1,stroke=1)
   label(x+bw/2,y+bh/2+(3 if sub else -3),title,10,color)
   if sub:label(x+bw/2,y+bh/2-13,sub,8.4,MUTED)
  if self.name in ('product','algorithm','pipeline','lifecycle','workstation','reviewrace'):
   specs={
    'product':[('连续来料','不停在中心'),('FPGA 检测','候选与局部框'),('最佳证据','按产品归档'),('人工复核','保留原图')],
    'algorithm':[('RGB → 灰度','整数加权'),('暗谷分数','四方向 / 半径8'),('双阈值支持','高90 / 低45'),('网格区域','最多8个框')],
    'pipeline':[('阶段 A','像素 n+3'),('阶段 B','像素 n+2'),('阶段 C','像素 n+1'),('阶段 D','像素 n')],
    'lifecycle':[('DMA 完成','槽内完整一帧'),('引用保留','候选最佳证据'),('TCP 发送','失败可重取'),('身份 ACK','引用归零释放')],
    'workstation':[('网络接收','校验身份/CRC'),('原图 + 掩码','保存并记摘要'),('复核页面','重新验证字节'),('人工结论','事务与修订号')],
    'reviewrace':[('打开 A','请求标记1'),('切到 B','标记2 / 清旧图'),('再次打开 A','标记3'),('旧 A 才返回','拒绝标记1')]
   }[self.name]
   gap=15;bw=(ww-36-gap*3)/4;y=hh-79
   for k,(a,b) in enumerate(specs):
    x=18+k*(bw+gap);box(x,y,bw,51,a,b)
    if k<3:line(x+bw+2,y+26,x+bw+gap-2,y+26)
   label(ww/2,14,{'pipeline':'流水填满后，各阶段同时处理不同像素','algorithm':'原图、时序、坐标沿并行延迟链保持对齐','reviewrace':'同一记录编号，不代表同一次异步读取'}.get(self.name,'身份、数据和完成条件必须一路对应'),9,MUTED)
  elif self.name=='architecture':
   box(18,82,138,47,'PL：图像运算','像素 / 掩码 / 区域',TEAL);box(181,82,138,47,'PS：采集服务','DMA / DDR / TCP');box(344,82,138,47,'PC：工作站','预览 / 证据 / 复核')
   line(158,106,179,106);line(321,106,342,106)
   box(18,17,138,43,'HDMI OUT','本地视频输出');line(87,80,87,61)
   box(181,17,301,43,'控制与状态回路','配置握手、健康、确认、版本身份');line(331,63,331,75)
  elif self.name=='clocks':
   box(18,83,132,47,'HDMI 输入时钟','74.25 MHz');box(183,83,132,47,'PixelClk','像素处理');box(347,83,135,47,'TX MMCM','VCO 742.5 MHz');line(152,107,181,107);line(317,107,345,107)
   box(18,17,145,46,'PS FCLK0','100 MHz / AXI');box(184,17,145,46,'PS FCLK1','200 MHz / 参考');box(350,17,132,46,'串行输出','371.25 MHz DDR');line(414,81,414,66)
  elif self.name=='reset':
   box(17,39,127,51,'原始锁定状态','可能异步变化');box(184,39,130,51,'共享像素复位','两级 / PixelClk');box(354,39,130,51,'共享参考复位','两级 / 200 MHz');line(146,65,181,65);line(317,65,351,65);label(ww/2,16,'失锁立即进入复位；恢复后按各目标时钟释放',9,MUTED)
  elif self.name=='window':
   sz=23;xx=30;yy=20
   for row in range(3):
    for col in range(3):
     c.setFillColor(TEAL if row==col==1 else colors.white);c.setStrokeColor(RULE);c.rect(xx+col*sz,yy+(2-row)*sz,sz,sz,fill=1,stroke=1);label(xx+col*sz+sz/2,yy+(2-row)*sz+8,chr(97+row*3+col),10,colors.white if row==col==1 else INK)
   box(153,52,135,37,'前两行缓存');box(153,10,135,34,'本行移位寄存器');line(109,55,145,55);box(328,30,149,51,'中心结果 e','延迟原图到同一位置');line(291,55,325,55)
  elif self.name=='valley':
   pts=[(25,82),(93,78),(164,76),(246,28),(328,72),(405,83),(476,78)]
   c.setStrokeColor(TEAL);c.setLineWidth(2)
   for a,b in zip(pts,pts[1:]):c.line(*a,*b)
   label(246,12,'中心较暗',9);label(84,93,'侧一',9);label(416,93,'侧二',9);label(355,35,'取两侧较小值，再减中心',10,GOLD)
  elif self.name=='regions':
   for y in range(4):
    for x in range(9):
     on=(x,y) in {(1,1),(2,1),(3,2),(6,1),(6,2)};c.setFillColor(TEAL if on else colors.white);c.setStrokeColor(RULE);c.rect(25+x*19,15+y*19,19,19,fill=1,stroke=1)
   line(212,53,251,53);box(263,30,211,48,'格子连通，像素边界','临近格可合并 / 不是像素级 CCL')
  elif self.name=='dma':
   box(17,69,132,47,'像素 + 帧尾','AXI Stream');box(184,69,132,47,'双时钟 FIFO','短时缓冲');box(351,69,132,47,'SG DMA','预排描述符');line(151,94,181,94);line(318,94,348,94)
   box(184,12,299,39,'DDR：48 个帧槽','当前采集与待发证据分离');line(417,67,417,53)
  elif self.name=='wiring':
   box(18,67,129,45,'笔记本 HDMI OUT');box(185,67,131,45,'PYNQ-Z2','HDMI IN → OUT');box(354,67,129,45,'显示器 HDMI IN');line(149,91,182,91);line(319,91,351,91)
   box(18,13,167,37,'电脑 USB → PROG/UART');box(222,13,261,37,'电脑 RJ45 - 网线 - 板卡 RJ45');line(170,51,219,64);line(352,51,293,64)

def blocks_to_flow(page):
 f=[]
 if page['lead']:f.append(para(page['lead'],'lead'))
 for b in page['blocks']:
  typ=b[0]
  if typ=='text':f += [para(b[1],'h'),para(b[2])]
  elif typ=='table':f += [para(b[1],'h'),tab(b[2],b[3]),Spacer(1,7)]
  elif typ=='note':
   t=Table([[para(b[1],'h')],[para(b[2],'small')]],colWidths=[CW]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),LIGHT),('LINEBEFORE',(0,0),(0,-1),3,GOLD),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,0),4),('BOTTOMPADDING',(0,0),(-1,-1),6)]));f += [Spacer(1,4),t,Spacer(1,6)]
  elif typ=='equation':
   t=Table([[para(b[1],'eq')]],colWidths=[CW]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),LIGHT),('BOX',(0,0),(-1,-1),.5,RULE),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]));f += [t,Spacer(1,5)]
   if b[2]:f.append(para(b[2],'small'));f.append(Spacer(1,8))
  elif typ=='diagram':f += [Diagram(b[1]),Spacer(1,7)]
  elif typ=='image':
   p=Path(b[1]);im=PILImage.open(p);w,h=im.size;scale=min(CW/w,250/h);f += [Image(str(p),w*scale,h*scale,hAlign='CENTER'),Spacer(1,6),para(b[2],'caption')]
 return f

