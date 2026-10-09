"""Text, geometry and contact-sheet checks after rendering every PDF page."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
from pypdf import PdfReader

R=Path(__file__).resolve().parents[2];Q=R/'reports/document_qa'
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
out=[]
for item in json.loads((Q/'outputs.json').read_text(encoding='utf-8')):
    path=Path(item['path']);reader=PdfReader(path)
    kind='film' if '拍摄' in path.name else 'manual'
    pages=sorted((Q/(kind+'_pages')).glob('page-*.png'))
    assert len(pages)==len(reader.pages)==item['pages']
    texts=[p.extract_text() for p in reader.pages]
    assert all(len(t)>100 and '\ufffd' not in t for t in texts)
    (Q/(kind+'_text.txt')).write_text('\n\n'.join(texts),encoding='utf-8')
    sheets=[]
    for start in range(0,len(pages),12):
        sheet=Image.new('RGB',(1200,4*452),'#dae3e7');draw=ImageDraw.Draw(sheet)
        for n,p in enumerate(pages[start:start+12]):
            with Image.open(p) as im:thumb=im.convert('RGB');thumb.thumbnail((284,416))
            x=(n%4)*300+8;y=(n//4)*452+24
            sheet.paste(thumb,(x,y));draw.text((x,y-20),f'{kind} / {start+n+1:02d}',font=font,fill='black')
        dest=Q/f'{kind}_contact_{start//12+1}.jpg';sheet.save(dest,quality=88);sheets.append(str(dest))
    out.append(dict(pdf=str(path),pages=len(pages),rendered=True,text_checked=True,contact_sheets=sheets))
(Q/'checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
