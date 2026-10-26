"""Follow the author's public large-file download form; no authentication.

The form is Google's ordinary 'too large to scan' download confirmation,
not a CAPTCHA or an access-control challenge. No executable is extracted.
"""
from pathlib import Path
from html.parser import HTMLParser
import urllib.request,urllib.parse,json,hashlib,time,zipfile
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');O=W/'v196_hfenet01';O.mkdir(exist_ok=False)
class Form(HTMLParser):
    def __init__(self):super().__init__();self.action=None;self.fields={}
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='form' and a.get('id')=='download-form':self.action=a['action']
        if tag=='input' and a.get('type')=='hidden':self.fields[a['name']]=a['value']
form=Form();form.feed((W/'v196_sources/download_probe.bin').read_text(encoding='utf8'))
assert form.action=='https://drive.usercontent.google.com/download' and form.fields['id']=='1geVxp-tgvEcoh_qkSAlUJmbcrk3g0SUU'
url=form.action+'?'+urllib.parse.urlencode(form.fields)
req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
started=time.monotonic();digest=hashlib.sha256();total=0;destination=O/'HFENet_Dataset.zip'
with urllib.request.urlopen(req,timeout=90) as response,destination.open('wb') as out:
    first=response.read(4)
    if first!=b'PK\x03\x04':raise ValueError('Not a public ZIP download; no access challenge will be bypassed')
    out.write(first);digest.update(first);total=4
    while block:=response.read(2*1024*1024):
        out.write(block);digest.update(block);total+=len(block)
        if total//(64*1024*1024)!=(total-len(block))//(64*1024*1024):print(f'Author public data {total}/895778218 bytes',flush=True)
        (O/'progress.json').write_text(json.dumps(dict(bytes=total,expected=895778218)),encoding='utf8')
assert total==895778218
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None
    entries=[dict(path=i.filename,bytes=i.file_size,crc32=i.CRC) for i in archive.infolist()]
(O/'entries.json').write_text(json.dumps(entries,indent=2),encoding='utf8')
(O/'source.json').write_text(json.dumps(dict(author_repo='https://github.com/RobotvisionLab/HFENet',author_folder='https://drive.google.com/drive/folders/1n2u-sAk_DXCr9bd_USaVTw_J8WSj6iXJ',file_id=form.fields['id'],bytes=total,download_sha256=digest.hexdigest(),zip_crc_verified=True,elapsed_seconds=time.monotonic()-started,license_scope='Repository software MIT; separate data redistribution terms not assumed'),indent=2),encoding='utf8')
print(json.dumps(dict(bytes=total,files=len(entries),examples=entries[:12])))
