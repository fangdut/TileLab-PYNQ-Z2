"""Keep the accepted V1.53 PDFs and prepend the V1.53.1 publication correction."""
from pathlib import Path
import io,json,shutil,hashlib
from pypdf import PdfReader,PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.colors import HexColor
R=Path(__file__).resolve().parents[2]
def main():
    pdfmetrics.registerFont(TTFont('AddSong','C:/Windows/Fonts/simsun.ttc',subfontIndex=0))
    pdfmetrics.registerFont(TTFont('AddHei','C:/Windows/Fonts/simhei.ttf'))
    style=ParagraphStyle('addendum',fontName='AddSong',fontSize=11,leading=19,wordWrap='CJK',textColor=HexColor('#253C4A'))
    accepted=R/'docs/accepted_v153';accepted.mkdir(exist_ok=True)
    results=[]
    for name,expected,film in [('TileLab_最终提交版_技术与教学手册.pdf',66,False),('TileLab_演示视频详细拍摄方案.pdf',17,True)]:
        p=R/'docs'/name;old=accepted/name
        if not old.exists():shutil.copy2(p,old)
        assert len(PdfReader(old).pages)==expected
        b=io.BytesIO();c=canvas.Canvas(b,pagesize=(595.276,841.89))
        c.setFillColor(HexColor('#143346'));c.rect(0,760,595.276,81,fill=1,stroke=0)
        c.setFillColor(HexColor('#ffffff'));c.setFont('AddHei',20);c.drawString(47,790,'TileLab · V1.53.1 最终提交修订')
        y=718
        entries=[
            '本页为修订说明。后续保留 V1.53 的完整手册和原页码；算法教学、线路连接、公式和拍摄流程继续适用。工程文件夹与 Vivado/Vitis 项目名保持 pynq_z2_tile_v1_53，电脑工作站运行版本为 1.53.1。',
            '本次仅修正工作站“验证记录”入口：读取 reports/v153/final_validation_summary.json，图片使用同批实际采集结果。原入口指向未随交付包含的 V1.48 报告；旧页面关于同步状态读取和硬件 V1.42 的说明已删除。',
            'PL 与 ARM 二进制、硬件时钟、裂纹算法和传输协议均未改变，沿用已接受的 V1.52。V1.53 核心实板证据保持原始版本身份，未将历史报告改称为新的测量。新增完整主机回归、HTTP 入口测试和 120 秒实板连续运动复测分别记录在 reports/v1531。',
            '产品边界：已校准纹理瓷砖的裂纹候选检测、局部红框、按产品最佳帧留存和人工复核。输入为真实照片的模拟连续运动；没有真实相机或工厂验收。独立大理石 24 张仅 1 张触发，像素召回约 1.92%，不得宣称通用材质准确率。',
            '演示拍摄请使用修订版 /benchmark 页，先展示适用范围，再展开原始证据。将 reports/v1531/summary.json 作为新增复测证据；图像识别指标仍按后续手册明确的样本分母说明。' if film else '复现时先执行 scripts/verify_submission.py 校验交付文件，再参考原手册的安装、生成工程、烧录和实测步骤。修订新增摘要见 reports/v1531/summary.json；V1.53 原冻结清单保存在 reports/accepted_baseline/V1_53_DELIVERY_MANIFEST.json。',
            'GitHub 地址只在实际上传成功后提供。此 PDF 不含账号凭据，不把本地 Git 提交冒充为远端发布。'
        ]
        for text in entries:
            flow=Paragraph(text,style);w,h=flow.wrap(501,650);assert y-h>70,(name,y,h)
            flow.drawOn(c,47,y-h);y-=h+16
        c.setFillColor(HexColor('#617685'));c.setFont('AddSong',9);c.drawString(47,42,'修订前言 · 后续页码沿用 V1.53 · 2026-10-09')
        c.showPage();c.save();b.seek(0)
        writer=PdfWriter();writer.append(PdfReader(b));writer.append(PdfReader(old));writer.add_metadata({'/Title':name.removesuffix('.pdf')+' V1.53.1'})
        with p.open('wb') as out:writer.write(out)
        reader=PdfReader(p);assert len(reader.pages)==expected+1
        assert '1.53.1' in reader.pages[0].extract_text()
        results.append(dict(path=str(p),pages=len(reader.pages),bottom_content_y=y,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    (R/'reports/v1531/pdf_addendum.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False))
if __name__=='__main__':main()
