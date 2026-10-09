"""Generate current-version report only from fresh passing evidence."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_31';O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=dict(source='source_audit.json',hardware='hardware_audit.json',firmware='firmware_audit.json',review_session='review_session_native.json',readiness='boot_readiness.json',real='real_board/summary.json',transport='transport_comparison.json',station='station_continuous.json',identity='station_identity_audit.json')
s={k:read(O/v) for k,v in files.items()};assert all(v['passed'] for v in s.values())
assert s['review_session']['tests']==19
log=(O/'host_tests.log').read_text();assert 'Ran 265 tests' in log and log.rstrip().endswith('OK')
assert s['real']['samples']==s['real']['pixel_exact']==50
assert s['transport']['byte_exact_triplets']==50 and s['transport']['packed_reconnect_same_event']
assert s['station']['saved']==s['identity']['physical_products']==10
assert s['hardware']['cdc_unsafe_endpoints']==0 and len(s['hardware']['max_delay_audit']['groups'])==8
old=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json')
limits=[v for v in old['limits'] if not ('TIMING-24' in v or 'overridden' in v.lower() or 'max-delay' in v.lower())]
limits.append('V1.32 activates all eight XPM CDC data-path maximum delays; remaining I/O and IP methodology warnings remain reported, not newly waived. This is not physical hotplug, long-duration factory or power-loss certification.')
summary=dict(version='V1.32',passed=True,unit_tests=265,**s,baseline_manifest_sha256=sha(B/'DELIVERY_MANIFEST.json'),test_scope='Fresh complete implementation, XPM max-delay endpoint coverage, reset netlist/recovery/removal, full Vitis build, actual JTAG/HDMI 50-photo regression, 50 same-event three-codec comparisons and reconnect, 60-second continuous best-evidence test. V1.31 reset RTL simulation inherited unchanged.',limits=limits)
(O/'packed_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
h=s['hardware'];r=s['real'];st=s['station'];ident=s['identity']
groups='\n'.join(f"| {g['name']} | {g['timed_endpoints']} | {g['requirement_ns']:.3f} | {g['minimum_slack_ns']:.3f} |" for g in h['max_delay_audit']['groups'])
transport='\n'.join(f"| {n} | {e['raw']['request_ms']:.3f} | {e['legacy']['request_ms']:.3f} | {e['compact']['request_ms']:.3f} |" for n,e in s['transport']['summary'].items())
report=f'''# Tile V1.32 跨时钟约束与实板收尾报告

## 本版完成了什么

本版硬件改动仅修正跨时钟时序约束，不改变像素算法、检测配方或频率。移除顶层 HDMI 与 PS 时钟之间一条过宽的 set_clock_groups，使原被其覆盖的八组 XPM set_max_delay -datapath_only 真正参与实现检查。保留已审查的单比特入口、复位和厂家 IP 例外，没有新加 false path 或 CDC waiver。测试中另修正 HDMI 播放窗口的鼠标指针污染，只在该窗口隐藏光标。

用户要求本版结束后暂停，因此不开始 V1.33。旧版 V1.31 原目录和轻量 ZIP 保留，备份 SHA256：{plan['backup_sha256']}。

## 修正依据

只读打开旧 routed DCP，先把原约束导出、清空再回放，确认 WNS/WHS/WPWS 保持 +0.186/+0.053/+0.264 ns，证明约束回放方法有效。再只删一条分组回放，原 8 个 TIMING-24 消失，实际端点被重新计时。这个试验不替代本版完整新构建。

随后从当前源码重新完成全部 IP 综合、顶层综合、布局布线、位流和 XSA 导出。逐组检查每个动态目标数据位都有对应时序路径，综合常量位另验证其直接 GND/VCC 驱动；最大延迟要求与 XPM 的 10/13.468/40/53.872 ns 一致。8 组 bus skew 另行通过。设计中厂家宏原有 waiver 保留，不声称从未使用厂家例外。

AMD 约束优先级参考：https://docs.amd.com/r/en-US/2026.1/ug1387-acap-hardware-ip-platform-dev-methodology/Clock-Exceptions-Precedence-Over-set_max_delay

## 实现与约束测量

WNS {h['wns_ns']:+.3f} ns；WHS {h['whs_ns']:+.3f} ns；WPWS {h['wpws_ns']:+.3f} ns。LUT {h['resources']['Slice LUTs']:g}、FF {h['resources']['Slice Registers']:g}、BRAM {h['resources']['Block RAM Tile']:g}、DSP {h['resources']['DSPs']:g}。

CDC 无 unsafe/unknown。共享复位 2+2 结构保留，旧重复入口为 0，两域 recovery/removal 都通过。像素 74.25 MHz、AXI 100 MHz、参考 200 MHz 不变。剩余 CKBF/LUTAR/PDRC/I/O 等方法学告警继续保留，不声称零告警。

| 约束组 | 实际计时目标位 | 要求 ns | 最小余量 ns |
|---|---:|---:|---:|
{groups}

## 固件与自动测试

完整 Vitis 平台/BSP/应用重建，固件版本 0x12000。在线视觉算法仍在 FPGA。相对 V1.31 固件业务逻辑不变，仅版本及说明变化；实际 ELF 审计确认 IRQ 浮点上下文保存、4096 字节 IRQ 栈和整数 memcpy。265 项主机测试、19 项前端复核会话测试通过。V1.31 的复位数字仿真作为明确标注的继承证据，本版没有伪称重新仿真相同 RTL。

首次后台启动遇到 Vitis 对中文 Windows 输出的 UTF-8 解码失败，且外层脚本退出码为零。固件审计因缺少新应用源而阻止继续下载。将构建控制台切换到 chcp 65001 后，平台/BSP/应用完整重建成功，再核验新 ELF；初次失败日志保留为 vitis_build_initial_encoding_failure.log。不能只凭批处理退出码判定构建成功。

## 实际上板测试

首轮回归在 real_004 停止：原图最右列顶部 17 像素与既定基准不同，实际图像对应的掩码、区域和三个 CRC 均正确。随后诊断读到一条保留事件，图中明确存在鼠标箭头，差异位于 (840,321)～(851,339)；后续五帧恢复完全一致。初始边缘残片与指针干扰相符，但不能仅凭 CRC 判断外部输入是否正确。修复是在 WPF 刺激窗口设置 Cursor=None、ForceCursor=true，不改系统全局指针，也不放宽像素比较。原失败图和诊断图保留在 real_board_initial_failure 与 rgb_diag_*，修复后重新进行完整回归。

新 BIT 与 ELF 经 JTAG 下载，启动身份匹配后才测试。50 张真实照片通过电脑 HDMI 输入实板，RGB 与既定 V1.24 原图基准一致；掩码、区域、面积与参考逐像素一致。17/17 裂纹图触发，0/33 正常图触发；像素召回 {r['pixel_recall']:.8f}，精确率 {r['pixel_precision']:.8f}。这是历史开发回归，不是独立工厂盲测。

50 组三种传输请求策略都来自同一队列事件，原始字节、描述符与三个 CRC 一致；噪声输入实际采用 PACK25，网络中断后重连仍取回同一事件。自适应 PACK 请求在 RLE 更小时仍使用 RLE，不能把所有请求都称为实际 PACK 编码。下表为每输入 10 组的请求时间中位数，不是线路线速或 PL 延迟。

| 输入 | RAW ms | 自适应 RLE ms | 自适应 PACK ms |
|---|---:|---:|---:|
{transport}

连续 {st['seconds']:.3f} 秒实际 HDMI 运动测试，主机接收 {st['host_captures']} 帧，保存 {st['saved']} 次异常产品经过的最佳帧；源条码身份审计对应 {ident['physical_products']} 次经过，最大中心距离 {ident['max_center_error_px']} 像素，均完整可见。这些来自照片重复移动，不代表独立实物样本数。没有新增 gap、invalid、dropped、ACK 或描述符 CRC 错误。本测试没有真实相机，没有物理断电拔线。

## 下一步空间（本次不实施）

1. 固定光源与相机，按实际产品独立划分标定和盲测；解决跨材料误报及无强种子弱裂纹漏检。
2. 通过 ROI 裁剪与缩略图降低证据字节，保留坐标变换和全帧身份证明；不先盲目提像素频率。
3. 做物理 HDMI/网线拔插、供电故障和更长压力试验；补足文件与数据库一致恢复、账户和完整复核历史。
4. 审查剩余板级 I/O 与厂家 IP 方法学告警，不能随意添加 blanket false path 消除报告。

完整 PDF 技术手册位于 docs/TileLab_PYNQ-Z2_项目技术手册_V1.32.pdf，包含系统分层、所有主要算法与实现、教学术语和操作流程。收尾工作站使用预览模式与 1 GiB 存档上限。
'''
(R/'docs/Tile_V1.32_跨时钟约束与实板报告.md').write_text(report,encoding='utf-8')
(R/'docs/V1.32_约束验证说明.md').write_text('# V1.32 约束验证完成\n\n仅删除一条过宽 clock group。八组最大延迟的动态目标位逐一计时，常量位另核对 GND/VCC 驱动；八组总线偏斜另行通过。复位结构、算法 RTL 与 IP 源码相对 V1.31 完全相同。详细新测证据见 reports/v132/max_delay_audit.json、hardware_audit.json 和完整实板报告。\n\n不将 inherited RTL 仿真描述为本次新测试，不添加时序或 CDC 豁免。当前版本完成后暂停扩版。\n',encoding='utf-8')
(R/'README.md').write_text('# TileLab V1.32\n\n已完成新硬件实现、Vitis 构建和真实 HDMI/网络回归。当前版本恢复八组跨域最大延迟约束，保留 V1.31 共享复位和 V1.24 四级检测。\n\n工程：pynq_z2_tile_v1_53.xpr；工作区：pynq_z2_tile_v1_53.sdk；工作站：host/open_workstation.bat。\n\n技术手册：[完整 PDF](docs/TileLab_PYNQ-Z2_项目技术手册_V1.32.pdf)。报告：[跨时钟约束与实板报告](docs/Tile_V1.32_跨时钟约束与实板报告.md)。最终清单 DELIVERY_MANIFEST.json 含版本、备份、源码/部署文件 SHA256 和测试依据。\n\n只读旧版 D:/Vivado/pynq_z2_tile_v1_31 及其 ZIP 已保留。本版结束后按用户要求暂停，不继续 V1.33。\n',encoding='utf-8')
(R/'host/benchmark.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>V1.32 验证结果</title><style>body{background:#eef5f5;color:#183749;font:16px/1.7 system-ui;max-width:1040px;margin:40px auto}main{background:white;padding:36px;border-radius:18px}h1,h2{color:#087e85}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.card{background:#edf5f5;padding:20px;border-radius:12px}b{font-size:26px}pre{white-space:pre-wrap;font:14px/1.6 monospace}a{color:#087e85}</style><main><a href="/">← 返回工作台</a><h1>V1.32 · 跨时钟约束验收</h1><p>八组 XPM 最大延迟恢复生效；新硬件、新 Vitis 构建、新实板回归。算法与频率未改变。</p><div class="grid"><div class="card"><b>8 / 8</b><br>最大延迟与目标位覆盖</div><div class="card"><b>50 / 50</b><br>真实照片像素与区域一致</div><div class="card"><b>50 组</b><br>同事件三种请求策略一致</div></div><h2>测试摘要</h2><pre id="result">正在读取当前版本报告</pre><h2>适用范围</h2><p>历史照片经 HDMI 回放；非现场相机盲测。残余 I/O 与 IP 方法学告警保留；物理热插拔、长时现场及断电恢复未认证。按用户要求本版收尾后暂停扩版。</p></main><script>fetch('/api/benchmark').then(r=>r.json()).then(s=>{document.querySelector('#result').textContent=JSON.stringify({version:s.version,passed:s.passed,wns_ns:s.hardware.wns_ns,whs_ns:s.hardware.whs_ns,cdc_unsafe:s.hardware.cdc_unsafe_endpoints,unit_tests:s.unit_tests,front_end_tests:s.review_session.tests,saved_products:s.station.saved,max_center_error_px:s.identity.max_center_error_px,active_max_delay:s.hardware.max_delay_audit.groups},null,2)}).catch(e=>document.querySelector('#result').textContent=e)</script></html>''',encoding='utf-8')
print('Fresh V1.32 summary, report, README and verification page generated.')
