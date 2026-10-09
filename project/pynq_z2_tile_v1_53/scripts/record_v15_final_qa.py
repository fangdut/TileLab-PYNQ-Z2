"""Record the completed final manual visual review, then verify release artifacts."""
from pathlib import Path
import json,hashlib,datetime
from pypdf import PdfReader
R=Path(__file__).resolve().parents[1];T=R/'reports/v15'
doc=R/'docs/Tile_V1.5_真实瓷砖优化与实板测试报告.docx'
pdf=T/'document_qa/report.pdf'
count=len(PdfReader(pdf).pages)
assert count==14
pages=[T/f'document_qa/page-{n:02d}.png' for n in range(1,count+1)]
assert all(p.is_file() for p in pages)
qa=dict(all_pages_visually_checked=True,page_count=count,
 reviewed_pages=list(range(1,count+1)),
 renderer='Microsoft Word own COM instance exported to PDF; bundled Poppler 120 dpi',
 canonical_renderer_attempt='document_renderer.log: unavailable bundled LibreOffice; no desktop LibreOffice used',
 observations='Every final page inspected: readable equations and tables, no clipping or overlap; removed orphan overflow page. Page 11 includes actual user monitor feedback.',
 document_sha256=hashlib.sha256(doc.read_bytes()).hexdigest(),
 page_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pages},
 checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
(T/'document_qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
ui=json.loads((T/'ui_checks.json').read_text(encoding='utf-8'))
ui['validated'].extend(['Final live T89 requested and applied match; preloaded real-photo conveyor selected',
 'Board snapshot counters show zero queue-full loss and invalid captures; two-second input-rate display around 60 fps',
 'Final real-photo evidence shows complete centered tiles with PL region boxes; screenshot workstation_final.png',
 'User confirmed external display continuously moving tiles with red crack boxes'])
ui['status']='PASS final live production UI visually verified'
ui['proof']='workstation_final.png'
(T/'ui_checks.json').write_text(json.dumps(ui,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(pages=count,document_bytes=doc.stat().st_size,ui=ui['status'])))
