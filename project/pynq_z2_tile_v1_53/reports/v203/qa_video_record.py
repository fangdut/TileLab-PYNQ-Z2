from pathlib import Path
import json,sys
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');sys.path.insert(0,str(W/'v193_qa_runtime'))
from playwright.sync_api import sync_playwright
O=W/'v203_materials01/video';qa=W/'v203_materials01/video_qa';qa.mkdir(exist_ok=False);results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport=dict(width=1920,height=1080))
    for file in sorted(O.glob('*.svg')):
        page.goto(file.as_uri());overflow=page.locator('text').evaluate_all('(els)=>els.map(e=>({text:e.textContent,x:e.getBBox().x,right:e.getBBox().x+e.getBBox().width,bottom:e.getBBox().y+e.getBBox().height})).filter(b=>b.x<0||b.right>1900||b.bottom>1080)');assert not overflow,overflow
        page.screenshot(path=str(qa/(file.stem+'.png')));results.append(dict(file=file.name,text_overflow=False))
    page.set_viewport_size(dict(width=1440,height=1000));page.goto((O/'拍摄提词预览.html').as_uri());assert page.locator('section').count()==7;assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');page.screenshot(path=str(qa/'提词预览.png'));browser.close()
(qa/'summary.json').write_text(json.dumps(dict(svg=results,storyboard_sections=7,planned_seconds=300,actual_video_recorded=False),ensure_ascii=False,indent=2));print(json.dumps(results))
