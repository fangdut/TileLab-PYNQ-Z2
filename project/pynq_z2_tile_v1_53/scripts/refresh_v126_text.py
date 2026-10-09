from pathlib import Path
R=Path(__file__).resolve().parents[1];p=R/'host/workstation.html';s=p.read_text(encoding='utf-8')
s=s.replace('自适应无损压缩 · 延迟优先','自适应游程压缩 · 兼容模式')
s=s.replace('默认优先延迟；省流模式额外压紧掩码，难压缩画面减少 21.875% 字节，但当前可能增加取图耗时。','默认保留原游程/原始策略；省流模式额外压紧掩码，难压缩画面减少 21.875% 字节。取图耗时随输入和传输开销变化，请查看实测。')
p.write_text(s,encoding='utf-8')
for name in ['report_v126.py']:
 p=R/'scripts'/name;s=p.read_text(encoding='utf-8').replace("default_policy='LATENCY_ADAPTIVE_RLE_RAW'","default_policy='LEGACY_ADAPTIVE_RLE_RAW'");p.write_text(s,encoding='utf-8')
p=R/'README.md';s=p.read_text(encoding='utf-8').replace('默认延迟优先，','默认保持原兼容策略，');p.write_text(s,encoding='utf-8')
print('UI describes selectable formats without promising one is always faster')
