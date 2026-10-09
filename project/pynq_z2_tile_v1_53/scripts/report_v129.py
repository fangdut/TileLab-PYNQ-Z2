from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132';B=R.parent/'pynq_z2_tile_v1_28'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=dict(firmware='firmware_audit.json',review_session='review_session_native.json',archive='archive_audit.json',station='station_continuous.json',identity='station_identity_audit.json',readiness='boot_readiness.json')
s={k:read(O/v) for k,v in files.items()};assert all(v['passed'] for v in s.values())
log=(O/'host_tests.log').read_text();assert 'Ran 246 tests' in log and log.rstrip().endswith('OK')
assert s['review_session']['tests']==11 and s['archive']['verified_http_reads']==40
prior=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json');c=s['station'];a=s['archive'];i=s['identity']
summary=dict(version='V1.29',passed=True,unit_tests=246,**s,baseline_manifest_sha256=sha(B/'DELIVERY_MANIFEST.json'),
 inherited_detection=dict(version='V1.24',hardware_sha256=plan['inherited_hardware_sha256'],scope='Unchanged PL detector; no new accuracy claim'),
 test_scope='Fresh host tests, actual browser state-machine tests, isolated copies of real evidence under file corruption, full Vitis build/programming, continuous board evidence and fresh HTTP reads. Prior full transport faults and physical drawing freeze not rerun.',limitations=prior['limits'])
(O/'packed_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
doc=f'''# Tile V1.29 存档完整性与复核实板报告

## 产品改进及职责

V1.29 让复核人员看到的是本次重新读取并核对过的原图和掩码。缺图、文件不可读或文件内容与保存时不一致，均有持续提示；原图和掩码没有同时通过检查时，不能提交复核。打开图片以后、提交之前又发生的损坏，也会被后端再次检查拦截。

FPGA 仍执行 720p60 裂纹候选提取、四级弱响应支持、区域框、产品识别与最佳帧选择，带像素及描述校验。Vitis/ARM 管理 DMA、DDR 帧槽、事件队列、确认、无损传输和有限恢复。电脑负责画面呈现、证据存档及人工复核，本版的 SHA256 属于文件完整性检查，不是把检测算法移到电脑。

本版 FPGA 电路、时钟和网络业务代码保持前版。建立了独立 Vivado 工程，完整重建 Vitis 平台、BSP 和应用，固件身份改为 0x11d00，完成实际 JTAG 下载。程序反汇编确认中断浮点寄存器保护、4096 字节 IRQ 栈、整数 memcpy 均保持。BIT/XSA/LTX 与 V1.24 硬件相同，没有声称本轮重新综合或提高了时钟。

## 先复现了什么问题

在独立目录中，直接运行未修改的 V1.28 存档读取代码，对测试 PNG 尾部追加字节。图片仍可以解码；旧接口仍返回 HTTP 200，虽然返回文件的 SHA256 已不同于数据库保存的 SHA256。旧版页面主要展示保存时的校验值，并不等于检查了本次读取。

反例保存在 `reports/v132/archive_baseline/summary.json`。这只是隔离的软件反例，不是宣称正常实板证据曾自行损坏。原工程和原证据从未被修改。

## 实现原理

对文件字节序列 B，计算 H = SHA256(B)。将本次 H 与保存时数据库记录 H_saved 比较；只有 `H == H_saved` 才返回该字节序列。这里比较的是文件字节，PNG 压缩方式不同也会改变 SHA256；因此它用来确认已保存文件是否改变，不用来比较两次不同编码的画面是否视觉相同。

读取函数一次最多读取 16 MiB 加一个检查字节，避免异常大文件无限占内存。它只打开文件一次；完成核对后直接发送内存中的同一份字节，不再按路径重新读取。这避免“第一次校验正常、第二次读取路径时文件已经被替换”的竞争。

读取失败返回结构化错误：不一致或无有效哈希返回 409，文件缺失、被独占等暂时不可读返回 503。文件、数据库和原复核结论均保留，不会自动删除、覆盖或凭空修复证据。正常响应包含本次已核对的 SHA256，并设 `Cache-Control: no-store`。

浏览器每次打开复核都重新请求原图和掩码，核对响应头与当前记录的保存哈希；不直接复用上一次 Image 解码结果。两个请求都成功后才显示画面并允许提交。失败会清空复核画布，显示常驻提示和“重新读取并校验”。重试保留未提交备注。

每次打开记录分配独立会话标记。A 记录切到 B，又切回 A，前一次 A 请求即使迟到也不能被当作当前 A 的结果；关闭弹窗会中止未完成请求。实际使用的浏览器 ReviewSession 类同时在 Node 中测试，覆盖迟到成功、迟到失败、关闭与重复打开。提交复核时，后端再核对原图和掩码，再修改结论。

界面明确区分“采集时 CRC”“保存时 SHA256”和“本次读取校验”，避免把过去通过的检查误解成此刻仍通过。CRC 用于 FPGA 到电脑链路的错误检查，SHA256 用于存档字节一致性；两者都不等于检测准确率。

## 分步测试

1. 246 项主机测试通过。本版新增 18 项读取/HTTP/提交检查，覆盖尾部附加字节、单字节变化、缺文件、缺哈希、坏元数据、16 MiB 上限、路径限制、真实 Windows 独占文件、校验后路径被替换、查看后才损坏以及实时预览不受存档逻辑影响。
2. 11 项实际浏览器会话类测试通过，页面内联脚本语法检查通过。完整主机测试没有因导入测试类而重复计数。
3. 在 8771 独立服务中复制两条 V1.28 真实板端证据；该服务禁止连接开发板。先正常打开，再只改副本原图；重新打开显示错误、清空画布、禁用提交，没有显示旧缓存。恢复副本后重试，草稿仍在。
4. 再在原图和掩码均已成功加载后，只改副本掩码；提交被拒绝，数据库原备注和结论没有变化。恢复后重试并提交测试备注成功。测试结束，两张原图和两张掩码均恢复到原始哈希；保留故障字节副本和截图，关闭独立服务。正式 V1.28 存档哈希完全未改。
5. 完整构建并实际下载 V1.29，等待匹配启动号、固件身份和完整 HDMI 帧后，再开始正式验收。
6. 实际运动源连续运行 **{c['seconds']:.3f} 秒**，主机取到 **{c['host_captures']} 张**抽样，板端完整帧计数增加 **{c['after']['captured']-c['before']['captured']}**，经过 **{c['after']['products_completed']-c['before']['products_completed']} 个**产品，保存 **{c['saved']} 个**缺陷产品各一张最佳图。
7. 保存图的掩码、框、区域面积与参考模型逐一相符，像素/响应头/PL 描述 CRC 全部通过。真实回放源帧码核对没有重复产品或已观测缺陷产品遗漏，最大居中偏差 **{i['max_center_error_px']} 像素**，满足既定 32 像素目标。本轮不是检测准确率盲测，也没有从一次运行的位置差异推断改进。
8. 对这 10 条新实板记录的原图与掩码各读取两次，共 **{a['verified_http_reads']} 次** HTTP 读取；响应字节、响应哈希、数据库哈希和磁盘文件全部一致，没有更改人工复核结论。取图结束后恢复仅预览，自动存档上限保持 1 GiB。

本版未重新执行全部历代网络故障和 WPF 冻结测试；其代码未改，历史证据仍归属原版本。新测试结果、源代码哈希、下载证明和截图均由 DELIVERY_MANIFEST.json 索引。

## 工程、使用与回退

工程 `{R.as_posix()}`；Vivado `{R.name}.xpr`；Vitis workspace `{R.name}.sdk`。ELF SHA256 `{s['firmware']['elf_sha256']}`。V1.28 原工程 `{B.as_posix()}` 保留，轻量 ZIP `{plan['backup']}`，SHA256 `{plan['backup_sha256']}`。ZIP 主要保留源码、文档和下载产物，全量素材和历史测试数据仍在旧工程。

保持电脑 HDMI → 开发板 IN → OUT → 显示器，1280×720 60 Hz；USB 接 PROG UART，网线直连电脑。停止旧工作台后用本版 `.sdk/program_ethernet.bat` 下载，运行 `host/start_station.ps1`。打开缺陷复核，等待本次读取通过，再选择结论和备注。失败时先检查文件或备份，恢复正确文件后用“重新读取并校验”；没有备份时不能凭此功能重建丢失证据。

## 限制和下一步

SHA256 这里不是数字签名。如果文件和数据库哈希同时被篡改，不能提供独立认证。提交检查只证明提交检查时刻的文件一致，不保证之后磁盘永远不变；已经显示的缩略图也可能来自此前有效读取，打开复核会强制重新核对。此次注入的是文件损坏、独占与缺失，并非整机断电或磁盘介质故障试验。

识别仍是候选检测：跨材质误报、弱裂纹像素漏检、真实相机曝光及运动模糊尚待验证；五个既有 CDC 不安全端点、有限事件队列和掉电前未传出图像无法恢复等限制保留。

下一步审查多窗口复核的并发提交：两个页面先后修改同一条记录时，旧页面可能覆盖新结论。先在隔离数据上复现，再用持久化修订号和条件更新解决，并验证重复提交、冲突恢复和服务重启边界；不把新的同步功能与检测算法升级混在同一版。
'''
report='docs/Tile_V1.29_存档完整性与复核实板报告.md'
(R/report).write_text(doc,encoding='utf-8')
(R/'README.md').write_text(f'''# TileLab V1.29

已完成存档原图/掩码本次读取校验、复核提交前再次检查，以及隔离故障注入和实板连续采集验收。旧工程和备份保留。

FPGA 硬件继承 V1.24，Vitis 业务逻辑保持 V1.26，固件身份 0x11d00。默认仅预览、自动存档上限 1 GiB。详见 [{report}]({report}) 与 DELIVERY_MANIFEST.json。

Vivado `{R.name}.xpr`；Vitis workspace `{R.name}.sdk`；下载 `.sdk/program_ethernet.bat`，启动 `host/start_station.ps1`。
''',encoding='utf-8')
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.29 实板验证</title><style>body{{margin:0;background:#eef5f5;color:#163e47;font:16px/1.8 system-ui}}main{{max-width:980px;margin:30px auto;padding:32px;background:white;border-radius:20px}}a{{color:#087d80}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card{{padding:18px;background:#edf7f5;border-radius:12px}}b{{display:block;font-size:30px}}.note{{padding:20px;background:#fff2e2;border-left:4px solid #b8792d}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}main{{margin:0;padding:20px}}}}</style><main><a href="/">← 检测工作台</a><p>V1.29 · 实板验收完成</p><h1>每次复核，重新确认原图与掩码</h1><p>本次读取校验与采集时 CRC 分开显示。文件缺失、不可读或发生变化时，保留证据与原结论，明确提示并阻止提交；恢复后可重试，草稿不丢失。</p><div class="grid"><div class="card">自动化检查<b>246 + 11 项</b>主机测试与实际会话类测试</div><div class="card">新实板证据读取<b>40 次一致</b>字节、响应头、存档哈希相符</div><div class="card">连续运动最佳证据<b>{c['saved']} 个产品</b>居中偏差 ≤ {i['max_center_error_px']} px</div></div><h2>损坏不能被旧缓存掩盖</h2><p>真实板端证据的独立副本先显示正常，再注入原图损坏，重新打开即被拦截；查看后损坏掩码，提交前再次检查仍能拦住。恢复副本后保留草稿并成功提交。原工程证据未修改。</p><h2>检测与采集链路继续实测</h2><p>本版完整构建 Vitis 并实际 JTAG 下载。正常运动 {c['seconds']:.1f} 秒保存 10 个缺陷产品各一张最佳图，掩码、框、区域面积和三层 CRC 核对通过。默认仅预览，避免无界落盘。</p><div class="note"><strong>完整性不等于识别准确率或防篡改认证</strong><p>本版未改 FPGA 算法、时钟与传输业务；没有新增准确率或提速结论。若图像与数据库同时被改，SHA 比对不能提供独立认证。跨材质、相机和既有 CDC 限制仍保留。</p></div><p><a href="/api/benchmark">完整验收 JSON</a> · {report}</p></main></html>'''
(R/'host/benchmark.html').write_text(html,encoding='utf-8')
print('Published measured V1.29 report and validation page')
