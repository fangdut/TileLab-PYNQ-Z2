from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_7'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
t=read(R/'reports/v132/transport_comparison.json');old=read(B/'reports/v17/transport_comparison.json')
motion=read(R/'reports/v132/motion_evidence_audit.json')
assert t['passed'] and all(v['functional_pass'] for v in motion.values())
assert 'Ran 61 tests' in (R/'reports/v132/host_tests.log').read_text(encoding='utf-8-sig')
assert read(R/'reports/v132/native_probe/result.json')['passed']
labels=dict(station_6='空传送带',station_1='合成裂纹',real_000='真实瓷砖 000',real_005='真实瓷砖 005',transport_noise='全画面随机噪声')
table=[];web=[]
for k,v in t['summary'].items():
 vals=[labels[k],str(int(v['compact_bytes'])),f"{v['saving_percent']:.6f}%",f"{v['raw_request_ms']:.2f}",f"{v['compact_request_ms']:.2f}",f"{old['summary'][k]['compact_request_ms']:.2f}"]
 table.append('| '+' | '.join(vals)+' |');web.append('<tr>'+''.join('<td>'+s+'</td>' for s in vals)+'</tr>')
motionrows=[]
for mode,name,sec in [('real_video','real',120),('ultrafast','synthetic',60)]:
 a=read(R/f'reports/v132/continuous/{mode}_{sec}s.json');v=motion[name]
 motionrows.append(f"| {mode} | {a['seconds']:.2f} | {a['raw_capture_fps']:.2f} | {a['host_captures']/a['seconds']:.2f} | {v['events']} | {a['max_interval_ms']:.1f} | {v['center_max_error_px']} |")
doc='''# Tile V1.8 自适应传输验证报告

## 本版产品变化

在 V1.7 完成无损压缩之后，本版解决不可压缩图像仍付出整帧编码成本的问题。FPGA 继续负责 V1.6 的弱裂纹提取、区域框、产品号、最佳截图以及连续采集；Vitis 中的 ARM 程序增加小规模重复率抽样，只选择传输格式。电脑还原所有 RGB 和掩码字节，不执行生产检测算法。

旧 V1.7 完整目录保留，另备份到 D:/Vivado/_baseline_backups/tile_v1_7_before_v1_8.zip。新工程与 .sdk 工作区均独立；RTL、BIT、XSA、LTX 沿用 V1.6，Vivado 重新建立工程/BD，Vitis 重新构建平台和 ELF 并实际下载。没有改变时钟，也没有声称重新实现了未改变的硬件。

## 为什么先判断再压缩

1280×720 的 RGB＋掩码为 3,686,400 字节。网络压缩有收益时值得编码；随机纹理中相邻像素大多不同，游程编码几乎无法缩小数据。

本版均匀分散选取 64 个块，每块 16 个像素，合计仅读取 4096 字节；计算 960 对相邻像素中完全相等的数量。重复率至少 50% 才尝试整帧游程编码，否则直接发送原始图像。该门槛是本机实验启发式，不是通用最优参数。误判只会影响传输效率，不会修改检测掩码、图像或缺陷判定。

尝试编码后仍检查上界和 5% 的最低收益；结果不理想就回退原始数据。保留原始模式开关。状态接口新增 compression_probe_bypasses 计数，区分预判直接回退。应用编译禁止内建 memcpy 替换，继续使用 V1.7 已实板验证的整数寄存器复制，避免这段路径重新引入浮点寄存器上下文风险。

## 实际开发板测量

每种输入选择 10 个事件，同一事件分别原始与自适应读取，交替顺序，比较全部字节和 40 字描述信息。耗时是中位数，包含响应等待、网络和解码，不包含 PNG 与存档。跨版本数据在不同时间采集，不能当作严格同时实验；本版的原始/自适应对照才是同事件 A/B。

| 输入 | 自适应载荷字节 | 载荷减少 | 本版原始 ms | 本版自适应 ms | V1.7 自动 ms |
|---|---:|---:|---:|---:|---:|
'''+ '\n'.join(table)+'''

50 组全字节对照通过，随机输入全部走原始传输，并观察到预判回退计数增加至少 10。主动中断图像传输后重连，仍取回原事件及全部字节；确认后队列才推进。合成裂纹场景的自适应请求仍比原始稍慢，不能宣称所有场景加速。

首次启动实验曾因 HDMI 播放器尚未完成空场景切换，阈值在 3 次取图内未应用而被断言拦截。测试脚本改为等待播放器场景确认，并在 5 秒内验证实际帧参数，保留原失败日志后重新执行全部对照；没有降低图像一致性要求。

随机噪声使用阈值 255，隔离检测过载，只用于传输检查；不能据此声称随机噪声下检测准确。两张真实瓷砖照片反复测量用于传输验证，不是新独立检测集。

## 连续运动验证

| 输入 | 测试秒数 | 板端 fps | 主机取图 fps | 留图数 | 最大主机间隔 ms | 最大居中误差 px |
|---|---:|---:|---:|---:|---:|---:|
'''+ '\n'.join(motionrows)+'''

保存事件逐一核对来源条码、产品身份、完整瓷砖以及掩码/框/面积，与离线参考一致。采集间隙、损坏帧和队列丢失无新增，观察到的缺陷产品无漏存、无重复物理产品、无正常产品误留。

居中精度目标仍为 32 像素。若高速审计超过该值，保留严格失败结果，不把功能通过改写为全部指标通过；具体值见上表与 motion_evidence_audit.json。缺陷检测能力和跨材质误报限制沿用 V1.6，本版没有提高识别召回率。

## 软件验证与复现

- 61 项软件回归通过，包括新版状态扩展与旧版兼容。
- 新增 280 组实际 C 抽样实现与独立参考比较，覆盖长度、边界与不同重复率，未读出范围。
- V1.7 编码器、整数复制和本地解码器核心未更改；其既有 690 / 1152 组验证见 V1.7 报告，本版不重复声称重跑。
- 本版实板 50 组相同事件对照、传输中断恢复、真实连续运动 120 秒和高速 60 秒。

下载使用 .sdk/program_ethernet.bat，启动使用根目录“启动以太网工作站.bat”；工作站默认仅预览，存档上限 1 GiB。停止当前服务后才能运行旧版本，回退运行 V1.7 的下载及启动脚本。JTAG 下载为易失配置，没有写 Flash。

## 下一版本

继续完善网络异常恢复与同步：短时网络故障采用有限时间自动重连，显式展示连接恢复状态和旧画面；损坏帧不确认、不伪装成恢复；用户暂停应停止后续重试。另发现独立测试进程写入证据后，工作站的图片容量缓存没有刷新，数值暂时偏小；本版完成测试后重启服务核对真实容量，下版修正跨进程计数同步。之后再评估更强的整帧 FPGA 校验、BSP 中断浮点上下文、高速最佳帧精度、物理掉电与拔线场景。板端队列只能暂存 12 个待确认事件，长时间断线仍可能丢失，不能宣称无限可靠。
'''
(R/'docs/Tile_V1.8_自适应传输验证报告.md').write_text(doc,encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.8

在 V1.7 无损传输基础上增加压缩收益预判，复杂纹理直接回退原始图像，FPGA 检测与 HDMI 时钟沿用 V1.6。

- 工程：pynq_z2_tile_v1_53.xpr；工作区：pynq_z2_tile_v1_53.sdk。
- 构建：scripts/create_project.tcl；.sdk/build_ethernet.py。
- 下载：.sdk/program_ethernet.bat；启动：“启动以太网工作站.bat”。
- 验证：scripts/board_v18_transport.py、board_v18_continuous.py、audit_v18_motion.py。
- 报告：docs/Tile_V1.8_自适应传输验证报告.md；证据：reports/v132；交付：DELIVERY_MANIFEST.json。
- 旧版完整保留且 ZIP 备份。默认仅预览，存档限额 1 GiB，避免无人值守占满磁盘。

算法与工业泛化限制、高速居中限制、物理断网测试边界详见报告。
''',encoding='utf-8')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.8 · 自适应传输验证</title><style>body{margin:0;background:#edf4f4;color:#173e47;font:16px/1.8 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1120px;margin:auto;padding:30px}a{color:#087d80}section{background:white;padding:24px;border-radius:18px;margin:20px 0}strong{font-size:28px;color:#087d80}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #dde7e8}.scroll{overflow:auto}.warning{border-left:5px solid #c87643;background:#fff3e9}</style><main><a href="/">← 返回工作台</a><p>V1.8 / 实际 HDMI、FPGA、DDR 与以太网</p><h1>跳过无效压缩，保留全部像素</h1><section><strong>50 / 50 同帧逐字节一致</strong><p>先抽样 4 KiB；有收益时压缩，不适合时直接发送原始数据。FPGA 检测逻辑保持 V1.6。</p></section><section><h2>实际板端传输结果</h2><div class="scroll"><table><tr><th>输入</th><th>载荷字节</th><th>减少</th><th>本版原始 ms</th><th>本版自适应 ms</th><th>V1.7 自动 ms</th></tr>'''+''.join(web)+'''</table></div></section><section class="warning"><h2>验证范围</h2><p>61 项回归、280 组抽样验证；实际中断恢复和连续运动测试。跨版本耗时不是同一时刻测量；本版两种模式是同事件 A/B。</p><p>真实照片只代表两个传输场景，不能扩大为检测准确率。随机噪声阈值 255；高速居中精度仍单独审计。下一版推进断线恢复与画面同步。</p><a href="/api/benchmark">完整测量数据 JSON</a></section></main></html>'''
(R/'host/benchmark.html').write_text(page,encoding='utf-8')
print('V1.8 report generated from completed tests')
