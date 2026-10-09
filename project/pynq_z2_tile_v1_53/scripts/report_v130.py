from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132';B=R.parent/'pynq_z2_tile_v1_29'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=dict(firmware='firmware_audit.json',review_session='review_session_native.json',review='review_audit.json',process_exit='review_process_exit/summary.json',station='station_continuous.json',identity='station_identity_audit.json',readiness='boot_readiness.json')
s={k:read(O/v) for k,v in files.items()};assert all(v['passed'] for v in s.values())
log=(O/'host_tests.log').read_text();assert 'Ran 265 tests' in log and log.rstrip().endswith('OK')
assert s['review_session']['tests']==19 and s['process_exit']['case_count']==3
prior=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json');c=s['station'];i=s['identity']
summary=dict(version='V1.30',passed=True,unit_tests=265,**s,baseline_manifest_sha256=sha(B/'DELIVERY_MANIFEST.json'),
 inherited_detection=dict(version='V1.24',hardware_sha256=plan['inherited_hardware_sha256'],scope='Unchanged PL detector; no new accuracy claim'),
 test_scope='Fresh host tests, actual browser revision/session tests, two real browser tabs on isolated evidence, abrupt SQLite process exits, full Vitis programming and continuous real board evidence. Unchanged complete transport fault suites not rerun.',limitations=prior['limits'])
(O/'packed_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
report='docs/Tile_V1.30_复核并发与持久化同步报告.md'
doc=f'''# Tile V1.30 复核并发与持久化同步报告

## 产品改进

V1.30 防止多个复核窗口以旧页面覆盖刚保存的新结论。每条记录有独立、持久化的复核修订号；打开时记住修订，提交时必须匹配。发生冲突时明确显示最新保存的结论与备注，原图和当前草稿保留，保存按钮禁用。点击“读取最新结论并保留草稿”，核对后才可再次提交。

FPGA 的 720p60 裂纹候选、四级邻域支持、区域框、产品识别、最佳证据选择及 CRC 没有改动。Vitis/ARM 继续管理 DMA、帧槽、确认和无损网络传输，业务逻辑没有变化，只将固件身份改为 0x11e00 并完整构建。电脑增加人工复核同步，没有执行视觉识别算法。本版已实际 JTAG 下载并运行连续 HDMI 测试。

## 先复现旧行为

用未修改 V1.29 的真实 HTTP 服务在隔离目录中建立测试记录。两个逻辑客户端先看到相同结论，A 先保存“确认裂痕”，B 从旧页面随后保存“误报”；旧接口两次均返回成功，A 的新结论被 B 覆盖。反例保存在 `reports/v132/review_baseline/summary.json`。正式项目记录没有被改动。

## 修订号和事务如何工作

记录的修订号记为 v，页面打开时读取 v_open。允许提交的条件是 `v_open == v_current`；成功后在同一事务内写入新结论、备注和 `v_new = v_current + 1`。即使结论改成 A、再改成 B、又改回 A，修订号仍前进，所以最初的旧页面不能因为内容相同就绕过检查。

修订号存于独立 SQLite 表，一条已编辑记录只需一个计数，不因每次复核不断新增历史行。原 events 表和图像不重写；旧数据库读取时没有修订记录的事件视为 0。修订号限制在 JavaScript 可精确表示的整数范围，达到上限会拒绝更新，不能回绕。

实现先用 `BEGIN IMMEDIATE` 获得写事务，再读取当前修订，比较后重新核对原图和掩码 SHA256，再写结论与修订，最后提交。SQLite 允许多个读事务，但同时只能有一个写事务；立即写事务使不同连接也不能同时读到旧修订并都完成更新。失败统一回滚，避免只改了结论、没改修订号。[SQLite 官方事务说明](https://www.sqlite.org/lang_transaction.html)

提交缺少有效修订返回 428，修订不匹配返回 409 并附当前记录，存储暂不可写返回 503。旧客户端没有修订号时不能静默继续写，需刷新到本版页面。进程内锁还负责保护同一连接；它与数据库事务作用不同，不能用其中一个代替另一个。

浏览器每次正常打开或明确“读取最新结论”都通过独立记录接口获取新修订，不依赖当前列表是否翻页或筛选。页面绑定的是本次打开的修订；后台列表刷新不能悄悄替换它。只重试图片读取不会自动采用新修订。迟到响应、A→B→A 快速切换和关闭窗口仍由独立会话标记隔离。

冲突时输入框保留草稿，另一区域显示最新已保存的结论及备注。明确载入最新修订后，输入框仍保留草稿并提示对照；用户可以修改草稿或取消，也可以在核对后作新的提交。这是防止无意覆盖，不是禁止用户有意识地修订结论。

## 测试顺序和结果

1. 完整主机测试 **265 项通过**；本版新增 19 项，覆盖初始修订、不同连接与同连接并发、旧请求、重复提交、内容来回变化、旧数据库结构迁移、修订持久化、事务中间失败、图像损坏、SQLite 写锁、整数上限及 HTTP/导出一致性。继承的存档完整性测试继续通过。
2. 实际浏览器会话类 **19 项通过**，其中新增 8 项检查修订绑定、迟到元数据、禁止悄悄更新修订、冲突禁用提交、明确重新打开和整数范围；页面脚本语法通过。
3. 三个独立子进程在真实 SQLite 事务边界使用 `os._exit` 强制退出：结论已写而修订未写、修订已写而提交未完成，重启均恢复原结论和修订 0，重试可成功；提交完成后退出，结论和修订 1 保留，旧请求重发冲突，不再增加修订。原图和掩码哈希全程相同。这是程序崩溃边界试验，不是整机断电或磁盘硬件故障试验。
4. 两个真实浏览器标签页打开同一条真实板端证据的独立副本，初始均为修订 1。A 保存后成为修订 2；B 的旧草稿提交被拦截，数据库仍为 A 的结论。B 的输入草稿不丢失，画面保留。B 明确读取修订 2、查看最新结论并修改后提交，成为修订 3。独立服务关闭，正式 V1.29 原图、掩码和人工结论均未改变。
5. Vivado 工程建立时第一次启动使用了错误的仅建工程环境变量名；在仍构建 Block Design 时停止本次进程，保留首轮日志。纠正为 `TILE_PREPARE_ONLY` 后重新建立成功，未将中断轮次当作通过。采用上一版经过验证的 BIT/XSA/LTX，未改变 FPGA 电路，未声称本轮重新综合实现。
6. 完整 Vitis 平台、BSP、应用构建通过，ELF 反汇编确认中断浮点保护、4096 字节 IRQ 栈和整数 memcpy。核对上一版 **{s['firmware']['baseline_source_files_verified']} 份**源文件哈希与备份哈希，下载后核对匹配启动号及有效 HDMI 帧。
7. 实板连续运动 **{c['seconds']:.3f} 秒**，主机接收 **{c['host_captures']} 张**抽样，板端完整采集计数增加 **{c['after']['captured']-c['before']['captured']}**，经过 **{c['after']['products_completed']-c['before']['products_completed']} 个**产品，保存 **{c['saved']} 个**缺陷产品各一张最佳图。最大居中偏差 **{i['max_center_error_px']} 像素**，符合 32 像素验收目标。
8. 掩码、区域框和区域面积与同图参考模型相符，像素、响应头和 PL 描述 CRC 通过；没有重复产品证据或已观测缺陷产品遗漏。对 10 条新记录及 20 张原图/掩码做 HTTP 读取，修订均为 0，字节及哈希一致，人工结论未改。未新增采集间隙、坏帧、队列丢失及 ACK/描述错误。

本版没有新的识别准确率、网络提速或时序收敛结论，未重复全部旧网络故障专项。一次回放的居中偏差波动不能证明算法改善。正式验收只留存约 4.2 MiB 图像，结束后恢复真实照片运动和仅预览模式，自动存档上限保持 1 GiB。

## 使用和回退

工程 `{R.as_posix()}`，Vivado `{R.name}.xpr`，Vitis workspace `{R.name}.sdk`。ELF SHA256 `{s['firmware']['elf_sha256']}`。上一版 `{B.as_posix()}` 完整保留；轻量备份 `{plan['backup']}`，SHA256 `{plan['backup_sha256']}`。不要让两个工程的主接收服务同时争用 8770 或开发板；本轮双页面测试使用隔离 8771 服务，且禁止访问开发板。

HDMI 连接为电脑输出 → 板上 IN → OUT → 显示器，1280×720 60 Hz；USB 接 PROG UART，网线直连电脑。用本版 `.sdk/program_ethernet.bat` 下载后运行 `host/start_station.ps1`。复核时先看“打开时已保存 · 修订 N”，再输入草稿。遇到冲突，先看较新的结论，再点击读取最新结论；核对后才能重新保存。

回退应恢复旧工程与其原数据库。旧程序不理解修订保护；不要让旧程序同时打开新版本正在使用的数据库。修订表只负责当前版本的条件提交，不是跨所有历史客户端的强制访问控制。

## 限制及下一轮

本版没有添加用户登录、多操作者身份或完整复核历史。修订号可阻止旧页面无意覆盖，不能阻止获得当前修订后有意修改，也不是数字签名。当前仍保留最新结论；审计追溯到每次人工修改属于后续功能。SQLite 写事务有限等待期间，其他使用同一 Records 锁的操作可能暂时延后；并非高并发数据库服务。

FPGA 候选检测仍存在弱裂纹漏检、跨材质误报和真实相机光照/曝光未验证问题。有限 12 事件队列、掉电前未传出图像无法恢复、HDMI 上一帧区域框等限制保留。下一轮回到 FPGA 跨时钟路径，核查既有五个 CDC 不安全端点的真实电路与约束，优先修复能明确证明的问题；通过仿真、综合实现及时序/CDC 对照后才考虑下载，不用放宽约束掩盖问题。
'''
(R/report).write_text(doc,encoding='utf-8')
(R/'README.md').write_text(f'''# TileLab V1.30

已完成持久化复核修订、旧页面覆盖保护、双窗口冲突流程、三种进程退出边界和真实开发板连续采集验收。旧工程及备份保留。

FPGA 硬件继承 V1.24；固件身份 0x11e00，Vitis 业务保持 V1.26。默认仅预览，自动存档上限 1 GiB。详见 [完整报告]({report}) 和 DELIVERY_MANIFEST.json。

Vivado `{R.name}.xpr`；Vitis workspace `{R.name}.sdk`；下载 `.sdk/program_ethernet.bat`，启动 `host/start_station.ps1`。旧客户端需刷新页面才能提交带修订号的复核。
''',encoding='utf-8')
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.30 实板验证</title><style>body{{margin:0;background:#eef5f5;color:#163e47;font:16px/1.8 system-ui}}main{{max-width:980px;margin:30px auto;padding:32px;background:white;border-radius:20px}}a{{color:#087d80}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card{{padding:18px;background:#edf7f5;border-radius:12px}}b{{display:block;font-size:30px}}.note{{padding:20px;background:#fff2e2;border-left:4px solid #b8792d}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}main{{margin:0;padding:20px}}}}</style><main><a href="/">← 检测工作台</a><p>V1.30 · 实板验收完成</p><h1>旧页面不能悄悄覆盖新结论</h1><p>每条复核记录使用持久化修订号。提交前核对图像与修订；发生冲突时显示最新结论，保留原图和草稿，明确重新读取后再决定是否提交。</p><div class="grid"><div class="card">自动化检查<b>265 + 19 项</b>主机测试与实际浏览器会话类</div><div class="card">程序中断边界<b>3 种通过</b>结论与修订一起提交或回滚</div><div class="card">连续运动最佳证据<b>{c['saved']} 个产品</b>居中偏差 ≤ {i['max_center_error_px']} px</div></div><h2>双窗口真实操作已验证</h2><p>两个页面打开修订 1。A 保存为修订 2，B 的旧请求被拦截且草稿保留。B 明确读取最新结论、核对后提交，成为修订 3。只更新独立证据副本，正式原图和结论未改。</p><h2>重新下载并运行真实 HDMI 测试</h2><p>正常运动 {c['seconds']:.1f} 秒保存 10 个缺陷产品各一张最佳图；掩码、框、区域面积与三层 CRC 相符。新存档的 10 条元数据、20 张原图和掩码重新读取一致。结束后恢复仅预览。</p><div class="note"><strong>并发保护仍不等于完整审计系统</strong><p>没有增加登录身份或每次修改的完整历史；修订号防止旧页面无意覆盖。本版未改 FPGA 算法、时钟或传输业务，没有新准确率或提速结论。CDC、跨材质及真实相机限制保留。</p></div><p><a href="/api/benchmark">完整验收 JSON</a> · {report}</p></main></html>'''
(R/'host/benchmark.html').write_text(html,encoding='utf-8');print('Published measured V1.30 report and verification page')
