from pathlib import Path
import datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v133';W=R/(R.name+'.sdk')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
plan=load(R/'ITERATION_PLAN.json');S=load(O/'validation_summary.json');B=Path(plan['baseline']);old=load(B/'DELIVERY_MANIFEST.json')
assert S['passed'] and S['unit_tests']['count']==275 and S['front_end']['tests']==19
assert len(S['process_exit']['exit_cases'])==4 and S['baseline_failure']['reproduced']
for rel,h in S['process_exit']['source_sha256'].items():assert sha(R/rel)==h,rel
assert load(O/'pdf_qa.json')['passed']
for group in ('source_sha256','proof_sha256'):
    for rel,h in old[group].items():assert sha(B/rel)==h,rel
assert sha(Path(plan['backup']))==plan['backup_sha256']
for rel,h in plan['inherited_hardware_sha256'].items():assert sha(W/rel)==h,rel
readme='''# TileLab V1.33 - 证据存档并发修复

状态：HOST_VALIDATED_ARCHIVE_WRITER_SERIALIZATION。电脑端修复已通过验证；本轮没有新的实板测试。FPGA 和 ARM 固件完全继承已验证的 V1.32，固件版本仍为 0x12000。

## 本版改进

`host/workstation.py` 的 `Records.save` 在检查事件身份之前执行 `BEGIN IMMEDIATE`，把身份检查、容量检查、两张 PNG 发布、事件插入和待确认登记纳入同一写者保留区间。不同连接/进程必须按顺序保存，失败写者不能先覆盖已提交图片再遭到数据库拒绝。失败时回滚数据库并释放写事务。视觉算法仍在 FPGA。

旧版缺陷已实际复现：frame 74 的记录完成保存与人工复核后，frame 73 的竞争写者覆盖 PNG，随后因 UNIQUE 失败；已有 SHA256 校验发现图像与记录不符。本版 10 项新增测试包含跨连接、独立进程、相同身份但不同图像/掩码、幂等重试、并发额度和写入失败。

## 验证与报告

- 主机全套 275 项通过，前端状态 19 项通过。
- 四个真实子进程强制退出点通过：第一张图后、第二张图后、事件 INSERT 后、COMMIT 后；已审核旧证据保持，未提交行/ACK 不可见，同编号重试正常。
- 两真实进程的同编号不同像素冲突通过，获胜证据不变。
- 新 Vivado XPR/BD 已生成并校验；98 个 PL/固件源文件与 V1.32 相同，BIT/XSA/LTX/ELF 哈希相同，因此未重新综合和实现。
- USB/JTAG 未枚举，169.254.200.10:9133 超时；新实板回归未进行。

正式 PDF：`docs/TileLab_V1.33_证据存档并发修复增补报告.pdf`（4 页，已逐页渲染检查）。全项目 59 页技术手册保留在原 V1.32/docs。详细验证：`reports/v133/validation_summary.json`；测试日志：`reports/v133/host_tests.log`；旧版复现：`reports/v133/baseline_save_race.json`；退出测试：`reports/v133/save_process_exit/summary.json`。

## 工程与运行

打开本目录 `pynq_z2_tile_v1_53.xpr`；正式脚本 `scripts/create_project.tcl` 可重新构建。此版本是主机改动，下载文件沿用 V1.32。`.sdk` 保留软件源与可下载 ELF，重新建立 Vitis 平台/BSP 可运行 `.sdk/build_ethernet.py`。已有板端二进制与本版兼容；若断电需要重新下载，使用 `.sdk/program_ethernet.bat`，启动 `启动以太网工作站.bat`。不要让两套接收服务同时抢同一块开发板。默认仅预览，存图上限 1 GiB。

## 回退与限制

V1.32 原工程未修改，轻量 ZIP：`D:/Vivado/_baseline_backups/tile_v1_32_before_v1_33.zip`。修改前核对 773 个源码及 56 个封存证据文件；ZIP 835 项内容逐项核验。轻量包不含全部历史运行素材。

这不是 PNG 与 SQLite 的跨介质原子事务。进程退出可能遗留未登记 PNG，同编号重试可以恢复；本版不自动删除这些文件，不宣称物理断电保障。保护只覆盖遵循 Records.save 的写者，外部程序不能任意覆盖证据目录。下一版优先用普通预览限速降低流量，同时优先接收报警；另安排孤立文件恢复机制，分开验收。
'''
readme=readme.replace('56 个封存证据文件',f"{len(old['proof_sha256'])} 个封存证据文件")
(R/'README.md').write_text(readme,encoding='utf-8')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>V1.33 验证报告</title><style>body{font:16px/1.8 system-ui;background:#eef5f5;color:#183749;max-width:1000px;margin:40px auto}main{background:white;padding:36px;border-radius:18px}h1,h2,a{color:#087e85}pre{font:13px/1.7 monospace;white-space:pre-wrap;overflow-wrap:anywhere}.note{padding:16px;background:#fff4dc;border-radius:10px}</style><main><a href="/">← 返回工作站</a><h1>V1.33 · 证据存档并发修复</h1><p>数据库写事务覆盖身份、容量、图片发布和确认登记，防止失败写者覆盖已提交证据。</p><p class="note">主机软件验证通过。FPGA 与固件沿用 V1.32；本轮设备不可连接，未进行新的实板验收。</p><p>275 项主机回归 · 19 项前端测试 · 4 个真实进程退出阶段 · 独立进程冲突通过。</p><h2>仍需解决</h2><p>PNG 与 SQLite 不是统一断电事务，异常退出可能留下未登记图片。同编号重试可以恢复，本版不自动删除。下一版计划优先降低普通预览流量。</p><h2>机器可读结果</h2><pre id="result">读取中</pre></main><script>fetch('/api/benchmark').then(r=>{if(!r.ok)throw Error('报告尚不可用');return r.json()}).then(s=>document.querySelector('#result').textContent=JSON.stringify({version:s.version,status:s.status,scope:s.scope,unit_tests:s.unit_tests,board_test:s.board_test,limits:s.limits},null,2)).catch(e=>document.querySelector('#result').textContent=e.message)</script></html>'''
(R/'host/benchmark.html').write_text(page,encoding='utf-8')
plan['phase']='VALIDATED_HOST_ONLY';(R/'ITERATION_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
sources={}
for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources'):
    for p in sorted((R/folder).rglob('*')):
        if p.is_file() and not any(part in ('__pycache__','runtime') for part in p.parts) and p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):
            sources[p.relative_to(R).as_posix()]=sha(p)
for p in W.iterdir():
    if p.is_file() and p.suffix in ('.py','.tcl','.bat'):sources[p.relative_to(R).as_posix()]=sha(p)
proofs=['README.md','ITERATION_PLAN.json','docs/TileLab_V1.33_证据存档并发修复增补报告.pdf']
proofs += [p.relative_to(R).as_posix() for p in O.rglob('*') if p.is_file() and p.suffix in ('.json','.log')]
size=0
for base,dirs,files in os.walk(R,followlinks=False):
    dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink() and not (Path(base)/d).is_junction()]
    size+=sum((Path(base)/n).stat().st_size for n in files)
manifest=dict(version='V1.33',status=S['status'],created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseline=str(B),backup=plan['backup'],backup_sha256=plan['backup_sha256'],hardware_revision=plan['hardware'],inherited_artifacts_sha256=plan['inherited_hardware_sha256'],source_sha256=sources,proof_sha256={n:sha(R/n) for n in sorted(set(proofs))},validation=S,size_bytes=size,report='docs/TileLab_V1.33_证据存档并发修复增补报告.pdf',limits=S['limits'])
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
progress=R.parent/'TileLab_进度与回退.md';text=progress.read_text(encoding='utf-8')
a=text.index('更新：');b=text.index('## 当前产品')
text=text[:a]+f"更新：{datetime.datetime.now().astimezone().isoformat()}\n\n最新软件验收版本：**V1.33**；最新实板验收仍是 **V1.32**。V1.33 为主机存档并发修复，275 项主机、19 项前端与真实进程故障测试通过。当前继续自主迭代。\n\n本轮工作站原服务未运行；USB/JTAG 未枚举且板端 TCP 超时，未声称新实板通过。\n\n"+text[b:]
text=text.replace('## 尚在进行','| V1.33 | 主机保存写事务覆盖图片发布；跨连接/进程竞争、4 阶段退出及 275 项回归 | HOST_VALIDATED_ARCHIVE_WRITER_SERIALIZATION | [报告](D:/Vivado/pynq_z2_tile_v1_53/docs/TileLab_V1.33_证据存档并发修复增补报告.pdf) |\n\n## 尚在进行',1)
text=text.replace('没有未封存的后续目录。','V1.33 已封存。下一版准备实现报警优先、普通预览限速；先备份，再修改，离板测试与实板验收分开记录。')
if '## 已按用户要求暂停扩版' in text:text=text[:text.index('## 已按用户要求暂停扩版')]+'## 恢复持续迭代\n\n2026-09-28 用户明确恢复自主迭代。V1.32 完整 PDF 手册作为历史基线保留，本轮以分版本增补报告记录新的变化。\n'
progress.write_text(text,encoding='utf-8')
print(json.dumps(dict(version='V1.33',status=manifest['status'],source_files=len(sources),proof_files=len(manifest['proof_sha256']),size_mib=round(size/1024**2,2))))
