from pathlib import Path
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1]
p=R/'host/workstation.html';s=p.read_text(encoding='utf-8')
marker='<div class="mini-status">'
assert s.count(marker)==1
s=s.replace(marker,'<div style="padding:0 24px"><div class="control-label"><label for="compression">网口传输</label></div><select id="compression" aria-label="网口传输"><option value="rle">自动无损压缩</option><option value="raw">原始数据对照</option></select><p class="footnote" id="wireInfo">等待传输数据</p></div>'+marker)
s=s.replace('function render(){const s=state,rs=s.records||[];','function render(){const s=state,rs=s.records||[];\nif(document.activeElement!==$(\'compression\'))$(\'compression\').value=s.compression_enabled?\'rle\':\'raw\';\nconst wf=s.frame;$(\'wireInfo\').textContent=wf?.wire_payload_bytes?`本帧 ${(wf.wire_payload_bytes/1048576).toFixed(2)} MiB · 减少 ${wf.wire_saving_percent.toFixed(1)}% · ${wf.wire_codec===\'WORD_RLE\'?\'无损压缩\':\'原始传输\'}；像素与掩码保持一致。`:\'等待传输数据\';')
s=s.replace("$('recipe').onchange=", "$('compression').onchange=e=>act('compression',{enabled:e.target.value==='rle'});\n$('recipe').onchange=")
p.write_text(s,encoding='utf-8')
p=R/'host/workstation.py';s=p.read_text(encoding='utf-8');s=s.replace("'station_6','burst'}|real_ids", "'station_6','transport_noise','burst'}|real_ids");p.write_text(s,encoding='utf-8')
p=R/'host/hdmi_display.ps1';s=p.read_text(encoding='utf-8');s=s.replace("if($c -notin @('video'","if($c -notin @('transport_noise','video'")
s=s.replace("}elseif($c -match '^station_[0-6]$'){", "}elseif($c -eq 'transport_noise'){\n    $script:phase='static';$media.Stop();$media.Visibility='Hidden';$image.Visibility='Visible'\n    $image.Source=New-Object System.Windows.Media.Imaging.BitmapImage([Uri](Join-Path $Root 'data/conveyor/transport_noise.png'))\n   }elseif($c -match '^station_[0-6]$'){")
p.write_text(s,encoding='utf-8')
Image.fromarray(np.random.default_rng(1701).integers(0,256,(720,1280,3),dtype=np.uint8)).save(R/'data/conveyor/transport_noise.png')
print('Transport controls and deterministic noise test stimulus created')
