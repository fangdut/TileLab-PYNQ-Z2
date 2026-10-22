from pathlib import Path
import json,hashlib,shutil
from html.parser import HTMLParser
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
out=P/'reports/v179';proof=json.loads((out/'verified_hdmi_overlap/verification.json').read_text());assert proof['continuous_hdmi_fps']==8.169552657504967
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class Images(HTMLParser):
    def __init__(self):super().__init__();self.sources=[]
    def handle_starttag(self,tag,attrs):
        if tag=='img':self.sources.extend(v for k,v in attrs if k=='src')
original=W/'v179_acceptance01/report.html';html=original.read_text();parser=Images();parser.feed(html)
for label in ['good','crack','identity_gray']:
    html=html.replace(label+'_snapshot/','verified_hdmi_overlap/'+label+'/snapshot/')
photos=json.loads((W/'v179_acceptance01/hdmi117/plan.json').read_text())['photos']
for ident in ['6621d769324f6e05d5838381','6621d769324f6e05d583835f']:
    row=next(r for r in photos if r['id']==ident);source=Path(row['file']);assert sha(source)==row['sha256']
    target=out/'originals'/source.name;target.parent.mkdir(exist_ok=True);assert not target.exists();shutil.copy2(source,target)
    html=html.replace(source.as_uri(),'originals/'+source.name)
target=out/'report.html';assert not target.exists();target.write_text(html,encoding='utf8')
(out/'report_export.json').write_text(json.dumps(dict(scope='PORTABLE_PRESENTATION_EXPORT_NOT_NEW_BOARD_EXPERIMENT',original_report_sha256=sha(original),portable_report_sha256=sha(target),change='Only local image paths rewritten; originals verified against source hashes'),indent=2)+'\n')
for folder in ['board_review_checks01']:
    source=W/('v180_'+folder);dst=P/'reports/v180'/folder;dst.mkdir(parents=True,exist_ok=False)
    shutil.copy2(source/'summary.json',dst/'summary.json');shutil.copy2(W/'test_v180_board_review01.py',dst/'reproduce.py')
repro=out/'reproduction'
for name in ['collect_v179_verified.py','checkpoint_v179_verified.py','start_v180_split125_physical01.py']:
    shutil.copy2(W/name,repro/name)
(out/'physical_pipeline01.json').write_bytes((W/'v179_physical_pipeline01.json').read_bytes())
p=R/'README.md';s=p.read_text(encoding='utf8')
start=s.index('| V179 资源重分配');end=s.index('\n',start)
s=s[:start]+'| **V179 已验证（HLS62）** | **117/117 原始照片及 HDMI 均通过；0/33 良品误报、17/17 裂纹；连续 239.548 秒完成 1,957 次自主检测，8.170 FPS；固定帧 8.021 FPS；ARM 双核暂停检查 119 次；100 MHz 时序通过** | 同一公开开发集；持续 10 FPS、独立盲测及精细定位仍待完成 |\n| V180 DDR 分流＋125 MHz | 沿用完全相同的 HLS62 检测内核；共享/分流实际端口与时钟检查通过 | 整机实现进行中；Winograd 仅完成独立数学检查，尚未接入检测器 |'+s[end:]
needle='最新已验证编译文件、实拍示例与实验记录见 '
assert needle in s;s=s.replace(needle,needle+'[V179 开发快照](deliverables/V179_Verified_HDMI_8p17FPS_Dev.zip)；[V179 实板报告](project/pynq_z2_tile_v1_53/reports/v179/report.html)；',1)
s+='\nV179 的 [实板证据](project/pynq_z2_tile_v1_53/reports/v179/verified_hdmi_overlap/verification.json) 绑定了原模型、匹配 BIT/XSA/ELF、全部 117 张结果和连续 HDMI 计数。连续吞吐比 V173 R2 提高约 22.56%，固定帧提高约 6.40%；整机 42,482 LUT、218 DSP、127.5 BRAM。源码冻结为 HLS62，Winograd 尚未集成。\n'
p.write_text(s,encoding='utf8')
p=R/'FPGA_MIGRATION_STATUS.md';s=p.read_text(encoding='utf8');where=s.index('\n\n')
new='''

Latest physically verified: **V179/HLS62, HW01, Acceptance01, boot1363500809**. All117 original-photo complete scores/masks remain exact; HDMI also117/117 correct,0/33normalFP,17/17cracks. Autonomous continuous HDMI: **1957detections /239.548seconds =8.169553FPS**,22.56% above V173R2. Fixed frame8.021126FPS (previous7.538925), about6.40% improvement. BothARMcores were checked halted119times;117distinct capturedphotoCRCs,zeroCPUperframestarts,noCPU/GPUinference. Frozenmodel andthreshold10908 unchanged. Public exposed development benchmark, not blind/painted-material/precise crack-tracing or finalcompetition acceptance. Sustained10FPS remains open.

Actual whole-video100MHz setup+0.013ns,hold+0.024ns,DRC0,bothFIFOGraybuschecks pass;42482LUT60203FF218DSP127.5BRAM. No physical repair required. Source30f6743bc2f1c71359fa2b3d3da3ce7d52b9b86078eea89438162afc9ce5a86a;BIT38936ea6894b7393db56f9c0cf11bf6abbe1351af80dc6149fafd402d17c3e07;XSA93f75a35058eb82fa8a4d3a6db7f115e40e195a207c1df637ee5ecf985fbe184;ELF8f9cf94ed91eaf3380ec6591bd1f286e8c1379d8afa493abe86429c09a104370. Source/model/boot/artifacts andactual retained four-slot capture buffers are bound in reports/v179/verified_hdmi_overlap. ZIP deliverables/V179_Verified_HDMI_8p17FPS_Dev.zip SHA41305dd8d66505f979870d9977c4bccbca974b5d1a1516907e9c44ca05da0ed7,sourcepin43e52652bc7e9ef6cfa4aadf5b1bdbeb8654c4a2. Earlier verified39 package is retained unchanged.

Current V180 experiment reuses exact HLS62 at125MHz with splitHP DDR topology (workHP0,modelHP2,input/resultHP3,captureHP1). Full implementation is running; no125MHz or newFPS result. SavedDDR connectivity/actualFCLK checks pass on existing shared/split BDs; wrongHP/clock/mastercount/requestedlayout fixtures are rejected. Physical result review now also rejects a zero-return helper whose accuracy status failed, nonhaltedARM,CPUframestarts,stale inputs or inconsistent FPS. The complete117-photo series defines its actual observation time; require at least180seconds, not an assumed fixed duration from the slower predecessor.

Winograd V180 is a separate **math-only** feasibility test, not integrated into either detector. It verifies576 bilinear coefficients and100208cases with exact scaled integer transforms, with conservative finite-width bounds; eligible10stride1DWlayers have55.56%fewer mathematical products, not an FPS claim. Actual16DSP sharing, memory ports,HLS/RTL andboard checks remain required. Winograd is priorwork: https://arxiv.org/abs/1509.09308 .

## Archived development history before V179 board verification
'''
s=s[:where]+new+s[where:];p.write_text(s,encoding='utf8')
print(json.dumps(dict(portable_report=str(target),original_image_sources=parser.sources,verified_scope=proof['scope'])))
