"""Seal test evidence and a brief changelog; no per-version formal report."""
from pathlib import Path
import datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v134';W=R/(R.name+'.sdk')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
plan=load(R/'ITERATION_PLAN.json');s=load(O/'validation_summary.json');B=Path(plan['baseline']);old=load(B/'DELIVERY_MANIFEST.json')
assert s['passed'] and s['unit_tests']['count']==295
http=load(O/'preview_http.json');assert http['passed'] and http['board_requests']==0
assert sha(R/'host/workstation.html')==http['html_sha256']==s['preview_ui']['html_sha256']
assert s['preview_ui']['tests']==11 and s['review_ui']['tests']==19
for rel,h in s['tcp_load']['source_sha256'].items():assert sha(R/rel)==h,rel
for group in ('source_sha256','proof_sha256'):
    for rel,h in old[group].items():assert sha(B/rel)==h,rel
assert sha(Path(plan['backup']))==plan['backup_sha256']
for rel,h in plan['inherited_hardware_sha256'].items():assert sha(W/rel)==h
s['http_smoke']=http;(O/'validation_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
readme='''# TileLab V1.34

状态：HOST_VALIDATED_EVENT_PRIORITY_PREVIEW_BUDGET。最新实板基线仍为 V1.32；本版仅改电脑端，FPGA / ARM 源码及 BIT/XSA/LTX/ELF 保持一致，固件版本 0x12000。

变更：以太网工作站默认普通预览上限 2 帧/秒，可选 5 或不限。队列中已有事件和人工抓拍优先，待确认 ACK 优先；空闲约 200 ms 查询状态，另加操作系统、网络与处理耗时。FPGA 持续检测。冻结预览仍接收报警，停止接收则停止新取图。切档/冻结/暂停与取图准入同步，迟到的前端状态不会覆盖新设置。档位为本次服务会话设置，重启后回到默认值。

验证：295 项主机测试、19 项复核 JS、11 项预览 JS 通过；真实 HTTP 设置回读与无硬件请求验证通过。真实回环 TCP 使用生产 EventTCP→EthernetBridge→Station→PNG/SQLite 路径，2/5/不限档都保留相同三个报警产品及一次人工抓拍，先落盘再 ACK，CRC/身份和字节计数一致。详见 reports/v134/validation_summary.json 和 preview_tcp_load/summary.json。回环的流量减少比例不可当成开发板吞吐提升；未进行新实板测试，浏览器控制接口失败，未声称浏览器视觉验收。

工程：打开 pynq_z2_tile_v1_53.xpr；.sdk 中保留源码与继承的下载文件，Vitis BSP 如需生成运行 build_ethernet.py。program_ethernet.bat 可重新下载，当前未烧录。启动以太网工作站.bat 启动主机，默认仅预览、1 GiB 存档上限。不要让两个接收程序争用同一开发板。

回退：原 V1.33 未修改，备份 D:/Vivado/_baseline_backups/tile_v1_33_before_v1_34.zip。上一版并发保存修复保留。剩余边界包括有限板端队列、PNG/SQLite 非统一断电事务、异常退出未登记文件、真实相机和现场识别精度未验证。下一版先修复未登记文件容量漏算并提供只读体检，避免擅自删除证据。

按用户要求，不逐版生成正式报告；保存本摘要与可复现测试记录，批量迭代后统一整理报告。
'''
(R/'README.md').write_text(readme,encoding='utf-8')
(R/'host/benchmark.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>V1.34 验证记录</title><style>body{font:16px/1.8 system-ui;background:#eef5f5;color:#183749;max-width:1000px;margin:40px auto}main{background:white;padding:36px;border-radius:18px}h1,a{color:#087e85}pre{font:13px/1.7 monospace;white-space:pre-wrap;overflow-wrap:anywhere}</style><main><a href="/">← 返回工作站</a><h1>V1.34 · 报警优先与普通预览限速</h1><p>295 项主机测试、30 项前端逻辑测试、真实 HTTP 与回环 TCP 对照通过。PL/固件沿用 V1.32；本版没有新的实板性能数据。</p><p>普通预览 2/5/不限；报警事件、人工抓拍和确认优先。空队列轮询等待约 200 ms，另加调度、网络和处理时间。</p><p>回环数据只验证电脑端协议和调度，不能作为开发板传输速度或识别精度。完整结构化记录如下。</p><pre id="result">读取中</pre></main><script>fetch('/api/benchmark').then(r=>r.json()).then(s=>document.querySelector('#result').textContent=JSON.stringify({version:s.version,status:s.status,unit_tests:s.unit_tests,tcp_load:s.tcp_load,limits:s.limits},null,2)).catch(e=>document.querySelector('#result').textContent=e.message)</script></html>''',encoding='utf-8')
plan['phase']='VALIDATED_HOST_ONLY';(R/'ITERATION_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
sources={}
for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources'):
    for p in sorted((R/folder).rglob('*')):
        if p.is_file() and not any(x in ('__pycache__','runtime') for x in p.parts) and p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):
            sources[p.relative_to(R).as_posix()]=sha(p)
for p in W.iterdir():
    if p.is_file() and p.suffix in ('.py','.tcl','.bat'):sources[p.relative_to(R).as_posix()]=sha(p)
proofs=['README.md','ITERATION_PLAN.json','reports/timing_summary.rpt']+[p.relative_to(R).as_posix() for p in O.rglob('*') if p.is_file() and p.suffix in ('.json','.log')]
size=0
for base,dirs,files in os.walk(R,followlinks=False):
    dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink() and not (Path(base)/d).is_junction()]
    size+=sum((Path(base)/n).stat().st_size for n in files)
manifest=dict(version='V1.34',status=s['status'],created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseline=str(B),backup=plan['backup'],backup_sha256=plan['backup_sha256'],hardware_revision=plan['hardware'],inherited_artifacts_sha256=plan['inherited_hardware_sha256'],source_sha256=sources,proof_sha256={n:sha(R/n) for n in sorted(set(proofs))},validation=s,size_bytes=size,report='README.md',limits=s['limits'])
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
progress=R.parent/'TileLab_进度与回退.md';text=progress.read_text(encoding='utf-8');a=text.index('更新：');b=text.index('## 当前产品')
text=text[:a]+f"更新：{datetime.datetime.now().astimezone().isoformat()}\n\n最新软件验收版本：**V1.34**；最新实板验收仍为 **V1.32**。本版普通预览限速及事件优先已完成，295 项主机、30 项前端、HTTP 与回环 TCP 验证通过。没有新实板性能声明。\n\n用户要求持续小步迭代，逐版备份和测试；不逐版制作正式报告，批量完成后汇总。\n\n"+text[b:]
text=text.replace('## 尚在进行','| V1.34 | 普通预览限速、队列/人工/ACK优先、切换准入与前端同步 | HOST_VALIDATED_EVENT_PRIORITY_PREVIEW_BUDGET | [摘要](D:/Vivado/pynq_z2_tile_v1_53/README.md) |\n\n## 尚在进行',1)
a=text.index('## 尚在进行');b=text.index('## 回退和空间')
text=text[:a]+'## 尚在进行\n\nV1.34 已封存，下一版准备修复孤立图片/临时文件的容量漏算，并增加只读存档体检。\n\n'+text[b:]
progress.write_text(text,encoding='utf-8')
print(json.dumps(dict(version=manifest['version'],status=manifest['status'],source_files=len(sources),proof_files=len(manifest['proof_sha256']),size_mib=round(size/1024**2,2))))
