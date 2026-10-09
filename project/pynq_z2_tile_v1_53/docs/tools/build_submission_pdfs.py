"""Build two navigable PDFs from measured current facts and teaching source."""
from pathlib import Path
import datetime,json,math
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Image
from reportlab.pdfbase import pdfmetrics
import page_layout as layout
from final_content import technical,filming

R=Path(__file__).resolve().parents[2];OUT=R/'docs';QA=R/'reports/document_qa';QA.mkdir(exist_ok=True)
W,H,M,CW=layout.W,layout.H,layout.M,layout.CW

def header(c,page,number,total):
    c.setFillColor(layout.NAVY);c.rect(0,H-15,W,15,fill=1,stroke=0)
    c.setFont('Arial',8);c.setFillColor(layout.MUTED);c.drawString(M,H-40,'TILELAB  /  PYNQ-Z2  /  COMPETITION SUBMISSION')
    c.setFont('Hei',9);c.setFillColor(layout.TEAL);c.drawString(M,H-66,page['part'])
    size=22
    while pdfmetrics.stringWidth(page['title'],'Hei',size)>CW and size>16:size-=.5
    c.setFont('Hei',size);c.setFillColor(layout.NAVY);c.drawString(M,H-100,page['title'])
    c.setStrokeColor(layout.RULE);c.line(M,43,W-M,43)
    c.setFont('Song',8);c.setFillColor(layout.MUTED);c.drawString(M,29,'V1.53 · 2026-10-09 · 竞赛原型，测试范围见正文')
    c.setFont('Arial',9);c.drawRightString(W-M,29,f'{number:02d} / {total:02d}')

def cover(c,title,subtitle,film):
    c.setFillColor(layout.NAVY);c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(layout.TEAL);c.rect(0,H-15,W,15,fill=1,stroke=0)
    c.setFont('Arial',11);c.setFillColor(colors.HexColor('#A7D4D3'));c.drawString(M,H-80,'TILELAB  |  FPGA VISION & EVIDENCE REVIEW')
    c.setFont('Hei',30);c.setFillColor(colors.white);c.drawString(M,H-152,'瓷砖裂纹检测系统')
    c.setFont('Hei',28);c.drawString(M,H-201,title)
    c.setFont('Song',13);c.setFillColor(colors.HexColor('#D4E5E8'));c.drawString(M,H-247,subtitle)
    c.setStrokeColor(layout.GOLD);c.setLineWidth(3);c.line(M,H-277,M+90,H-277)
    lines=['真实连接与不停带运行','完整镜头表与操作顺序','讲解稿、字幕与证据关联','检查、补拍与交付清单'] if film else ['产品目标与三层架构','算法公式与硬件实现','当前实测与适用边界','术语教学、实验与答辩']
    for i,line in enumerate(lines):
        c.setFont('Arial',13);c.setFillColor(layout.GOLD);c.drawString(M,H-330-i*43,f'{i+1:02d}')
        c.setFont('Song',14);c.setFillColor(colors.white);c.drawString(M+40,H-330-i*43,line)
    c.setFillColor(colors.HexColor('#234B5D'));c.roundRect(M,151,CW,132,12,fill=1,stroke=0)
    c.setFont('Hei',14);c.setFillColor(colors.white);c.drawString(M+18,242,'FPGA → ARM / Vitis → 电脑工作站')
    c.setFont('Song',11);c.drawString(M+18,212,'720p60 · 连续运动 · 产品最佳证据 · 人工复核')
    c.drawString(M+18,184,'真实照片回放验证，未完成工业相机与工厂验收')
    c.setFont('Hei',13);c.drawString(M,111,'PYNQ-Z2 · Zynq-7020 · Vivado / Vitis 2025.2')
    c.setFont('Song',11);c.setFillColor(colors.HexColor('#A7D4D3'));c.drawString(M,85,'最终提交候选工程 V1.53  |  2026 年 10 月 9 日')
    c.drawString(M,62,'包含实际限制与失败实验；不把仿真或开发样本冒充工厂认证')
    c.bookmarkPage('cover');c.addOutlineEntry('封面','cover',0);c.showPage()

def build(pages,name,title,subtitle,film=False):
    toc=math.ceil(len(pages)/28);total=1+toc+len(pages);path=OUT/name
    c=canvas.Canvas(str(path),pagesize=(W,H),pageCompression=1)
    c.setTitle('TileLab '+title+' - V1.53');c.setAuthor('TileLab 项目组');c.setSubject(subtitle)
    cover(c,title,subtitle,film)
    for part in range(toc):
        meta=dict(part='CONTENTS · 阅读导航',title='目录'+('（续）' if part else ''))
        header(c,meta,part+2,total);y=H-133
        for i,p in list(enumerate(pages))[part*28:(part+1)*28]:
            c.setFont('Song',10.5);c.setFillColor(layout.INK);c.drawString(M,y,p['title'])
            c.setFont('Arial',10);c.setFillColor(layout.TEAL);c.drawRightString(W-M,y,str(i+toc+2))
            c.linkRect('',f'p{i}',(M,y-3,W-M,y+13),relative=0,thickness=0)
            c.setStrokeColor(layout.RULE);c.setLineWidth(.25);c.line(M,y-8,W-M,y-8);y-=21.3
        c.showPage()
    metrics=[]
    for i,p in enumerate(pages):
        number=i+toc+2;header(c,p,number,total);c.bookmarkPage(f'p{i}');c.addOutlineEntry(p['title'],f'p{i}',0)
        flow=layout.blocks_to_flow(p);sizes=[f.wrap(CW,10000) for f in flow];height=sum(h for _,h in sizes);y=H-124
        if height>y-58:raise ValueError(f'{name} page {number}: {p["title"]}: content {height:.1f} too tall')
        for f,(w,h) in zip(flow,sizes):
            y-=h;f.drawOn(c,M+(CW-w)/2 if isinstance(f,Image) else M,y)
        metrics.append(dict(page=number,title=p['title'],content_height=height,bottom=y));c.showPage()
    c.save()
    (QA/(('film' if film else 'manual')+'_layout.json')).write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    return dict(path=str(path),pages=total,bytes=path.stat().st_size,minimum_bottom=min(x['bottom'] for x in metrics))

def main():
    s=json.loads((R/'reports/v153/final_validation_summary.json').read_text(encoding='utf-8'))
    assert s['engineering_acceptance'] and s['universal_material_recognition_accepted'] is False
    outputs=[build(technical(s,R),'TileLab_最终提交版_技术与教学手册.pdf','完整技术与教学手册','从实际像素、电路与事件，理解整个项目如何工作'),
             build(filming(s),'TileLab_演示视频详细拍摄方案.pdf','演示视频详细拍摄方案','接线、预检、镜头、讲解、剪辑与补拍的完整步骤',True)]
    (QA/'outputs.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(outputs,ensure_ascii=False))
if __name__=='__main__':main()
