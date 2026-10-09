from pathlib import Path
import json,hashlib,datetime,html
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_6'
def read(p):return json.loads((R/p).read_text(encoding='utf-8-sig'))
t=read('reports/v132/transport_comparison.json');motion=read('reports/v132/motion_evidence_audit.json')
assert t['passed'] and all(v['functional_pass'] for v in motion.values())
assert 'Ran 60 tests' in (R/'reports/v132/host_tests.log').read_text(encoding='utf-8-sig')
labels=dict(station_6='空传送带',station_1='合成裂纹',real_000='真实瓷砖 000',real_005='真实瓷砖 005',transport_noise='全画面随机噪声')
rows=[];webrows=[]
for k,v in t['summary'].items():
 payload=f"{v['compact_bytes']/1048576:.6f}" if v['compact_bytes']<1024 else f"{v['compact_bytes']/1048576:.3f}"
 saving=f"{v['saving_percent']:.6f}%" if v['saving_percent']>99.99 else f"{v['saving_percent']:.2f}%"
 vals=[labels[k],str(v['samples']),payload,saving,f"{v['raw_request_ms']:.2f}",f"{v['compact_request_ms']:.2f}"]
 rows.append('| '+' | '.join(vals)+' |');webrows.append('<tr>'+''.join('<td>'+x+'</td>' for x in vals)+'</tr>')
motionrows=[]
for mode,name,seconds in [('real_video','real',120),('ultrafast','synthetic',60)]:
 a=read(f'reports/v132/continuous/{mode}_{seconds}s.json');v=motion[name]
 saving=100*(1-sum(r['wire_payload_bytes'] for r in a['rows'])/(3686400*len(a['rows'])))
 motionrows.append(f"| {mode} | {a['seconds']:.2f} | {a['raw_capture_fps']:.2f} | {a['host_captures']/a['seconds']:.2f} | {saving:.2f}% | {v['events']} | {v['center_max_error_px']} |")
doc='''# Tile V1.7 无损传输优化与验证报告

## 产品与版本边界

V1.7 保留 V1.6 的 FPGA 弱裂纹检测、产品编号与最佳截图选择，本版只改变传输与电脑解码。图像依旧来自开发板实际 HDMI 采集，检测掩码和红框依旧由 FPGA 产生。没有用电脑重新检测，也没有丢弃颜色或裁剪原图来缩小字节数。

工程位于 D:/Vivado/pynq_z2_tile_v1_53；Vivado 工程和 .sdk 工作区独立。RTL、BIT、XSA 与 V1.6 完全相同，本版继承其已通过的时序结果，不声称又完成了一次新的 FPGA 布局布线。Vitis 平台和本版 ELF 已实际构建、下载。V1.6 原目录保留，另有 _baseline_backups/tile_v1_6_before_v1_7.zip 源码及下载产物备份，带逐文件哈希。

## 无损传输怎么做

每个像素原本占 4 字节：蓝、绿、红与 FPGA 候选掩码。1280×720×4=3,686,400 字节。大块背景包含很多连续相同的像素，用“重复次数＋像素值”可表达相同内容；没有连续重复的部分直接存原值。本版以 32 位字为单位，标签最高位表示重复，其余位表示数量；连续相同至少 3 个字才编码为重复段。

节省比例 = 1 − 实际图像载荷字节数 / 3,686,400。该指标不包含 TCP/IP、以太网包头。只有压缩后减少超过 5% 才发送压缩格式，否则发送原始数据。CPU 执行的是无损数据打包，不参与裂纹判定。电脑解码后恢复完整 1280×720 原图与掩码，后面的同帧坐标校验和留图流程保持不变。

ARM 每次最多处理 2048 个像素。先将 8 KiB 连续输入复制到小缓存块，再执行编码；每批返回主循环，让 DMA 回收、产品事件和网络维护继续运行。源 DDR 槽仍由事件队列持有；编码输出在 TCP 发送结束或连接中断之前保持不变；应用层确认仍决定何时释放事件。输出缓冲区有严格上限，遇到不可压缩输入时不会越界或增加载荷。

电脑新增可选的 Windows x64 本地解码器，源代码随工程提供。没有 DLL 时仍可用 Python 解码，结果应相同但速度较慢。界面可切换“自动无损压缩”和“原始数据对照”，每帧显示实际载荷与节省比例。

## 实板测量

对每个静态场景取 10 个事件，同一事件分别读取原始与压缩格式，交换读取顺序，比较全部像素、掩码与 40 字描述信息。以下耗时为中位数，包含等待图像、网络传输和解码，不包括 PNG 编码与磁盘保存。

| 输入 | 同帧对照数 | 压缩载荷 MiB | 载荷减少 | 原始请求 ms | 自动压缩请求 ms |
|---|---:|---:|---:|---:|---:|
'''+ '\n'.join(rows)+'''

50 组对照全部逐字节一致。真实照片为两个已有 MVTec 样本，每张重复 10 次用于传输实验，不能算作 20 张新的检测样本。随机噪声使用高阈值 255 隔离检测通路，只验证不可压缩数据的回退，不代表通过了高噪声缺陷检测。

两张真实图的请求延迟降低约 11%～12%，数据量降低约 72%。全随机噪声虽然正确回退，仍需先尝试编码，所以延迟增加。下一版优先加入廉价可压缩性预判，避免这项开销；不把全场景加速作为本版结论。

## 测试确实发现并修复的问题

第一版逐像素读取未缓存的 DDR，虽然减少了网口字节，但取图更慢，被实测拦截。改为分块读取后，又在实际对照中发现偶发两个 32 位字不一致，保存了失败数据，没有继续把它当作无损成功。

检查最终可执行文件，标准库 memcpy 使用 VFP 浮点寄存器，而本配置的 IRQHandler 只保存整数寄存器。这与长复制被中断时寄存器遭覆盖的现象相符。本版提供整数寄存器的通用 memcpy：对齐数据用 LDM/STM 连续搬运，未对齐和尾部使用字节访问，不关闭中断，不改变 DMA 内存属性。实际链接反汇编保存在 reports/v132/integer_memcpy_disassembly.txt。修正后重新构建、重新烧录并通过完整实板对照。

这一修复不等于所有库函数的中断上下文问题都已经排除。后续仍需审核 BSP 的浮点上下文约定，并增加由 FPGA 产生的整帧校验，以覆盖颜色数据在缓存和软件中的异常；当前候选数量与区域校验不能发现所有颜色字节损坏。

## 连续运动与断开恢复

| 输入 | 实际秒数 | 板端采集 fps | 电脑取图 fps | 平均载荷减少 | 完整事件截图 | 最大居中偏差 px |
|---|---:|---:|---:|---:|---:|---:|
'''+ '\n'.join(motionrows)+'''

两个计时窗口均核对了每张证据的来源条码、物理产品编号、候选掩码和区域面积；产品无重复、无观察到的缺陷漏存、无正常产品误留。采集间隙、损坏帧、队列丢弃均无新增。高速最差居中偏差仍为 40 像素，未达到 32 像素目标；严格审计保留非零退出和失败状态，不计为全部指标通过。高速窗口曾出现一次 TCP 重传并重连，最长电脑取图间隔约 594 毫秒；自动重取未确认事件后继续完成，无新增漏存。板端 60fps 不等于电脑预览从不短暂延迟。

还主动在图像载荷传输中断开 TCP，重连后读取同一未确认事件，全部字节相同；只有最终应用确认才推进队列。这是软件注入的连接中断测试，不等于已测试拔线、掉电与所有交换机行为。

## 验证范围

- 60 项电脑软件回归，通过。
- 690 组实际固件编码器 C 测试，覆盖长重复、短重复、随机字、工作分块和输出上界；同时对照 Python 与本地解码器。
- 1152 组 memcpy 对齐、长度、返回地址与边界契约检查；ARM 指令路径由实板全帧比较验证。
- 本地解码器另有 2000 组随机异常流检查，验证输出保护区不被修改并对照 Python 拒绝规则。
- 50 组实板同事件逐字节对照、连接中断恢复，以及真实照片/高速合成连续运动测试。

## 使用、存储与后续

运行本目录 .sdk/program_ethernet.bat 下载，随后运行根目录“启动以太网工作站.bat”。只运行一个版本的工作站与 HDMI 输入播放器。默认仅预览，不自动堆积截图；存档上限 1 GiB。材料仍选“本机 HDMI 瓷砖 · 弱裂纹增强”，高/低阈值 89/45。输入保持 1280×720、60 Hz。

要回退，停止本版工作站和播放器，运行 V1.6 目录的下载及启动脚本，不混用 ELF、BIT 与工作区。此次 JTAG 下载未写 Flash，断电后需重新下载。

下一步按小版本推进：先跳过不可压缩画面的编码，随后增加短暂断网后的有界重连、区分陈旧证据与实时画面、完善暂停/人工请求语义和帧身份校验，再考虑 FPGA 整帧校验及物理断链恢复。检测本身仍有弱裂纹覆盖不足、跨材料误报、相邻产品分离和 HDMI 上一帧框滞后的限制，本版没有消除这些问题。
'''
(R/'docs/Tile_V1.7_无损传输优化报告.md').write_text(doc,encoding='utf-8')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.7 · 无损传输验证</title><style>body{margin:0;background:#edf4f4;color:#173e47;font:16px/1.8 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1080px;margin:auto;padding:30px}a{color:#087d80}section{background:white;padding:24px;border-radius:18px;margin:20px 0}.metrics{display:flex;gap:35px;flex-wrap:wrap}strong{font-size:28px;color:#087d80}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #dde7e8}.scroll{overflow:auto}.warning{border-left:5px solid #c87643;background:#fff3e9}</style><main><a href="/">← 返回工作台</a><p>V1.7 / 实际 HDMI、FPGA、DDR 与以太网</p><h1>保持全部像素，减少传输量</h1><section class="metrics"><div>真实瓷砖图载荷减少<br><strong>约 71.9%</strong></div><div>同一事件逐字节一致<br><strong>50 / 50</strong></div><div>识别电路<br><strong>沿用 V1.6</strong></div></section><section><h2>实板原始与无损传输对照</h2><p>每场景 10 个事件；请求耗时为中位数。相同事件分别读取两次，保持图像、掩码、红框与产品号一致。</p><div class="scroll"><table><tr><th>场景</th><th>对照数</th><th>载荷 MiB</th><th>减少</th><th>原始 ms</th><th>自动 ms</th></tr>'''+''.join(webrows)+'''</table></div></section><section class="warning"><h2>测量边界</h2><p>两张真实照片重复测量，不是新增检测准确率。全噪声会回退原始数据，但仍付出尝试压缩时间。下一版优化这个开销。</p><p>裂纹识别能力沿用 V1.6：历史裂纹像素召回率 22.62%，跨材质误报和高速居中限制仍存在。板端处理率与电脑预览率分别统计。</p></section><section><h2>有据可查的可靠性</h2><p>60 项软件测试、690 组编码边界检查、1152 组复制契约检查通过。50 组实板同帧全字节对照通过；主动中断传输后取回同一事件。</p><p>实测拦截过浮点寄存器复制的偶发错误，修正为整数复制后重新构建并下载。失败日志和数据保留在工程报告目录。</p><a href="/api/benchmark">完整传输数据 JSON</a></section></main></html>'''
(R/'host/benchmark.html').write_text(page,encoding='utf-8')
p=R/'host/workstation.html';p.write_text(p.read_text(encoding='utf-8').replace('弱裂纹验证 ↗','传输与检测验证 ↗'),encoding='utf-8')
(R/'README.md').write_text('''# PYNQ-Z2 Tile V1.7

V1.6 FPGA 弱裂纹算法 + 可回退原始传输的无损网口压缩。新工程独立，原版保留并有 ZIP 备份。

- Vivado：pynq_z2_tile_v1_53.xpr。RTL/硬件文件继承已验证的 V1.6，scripts/create_project.tcl 可从零构建。
- Vitis：pynq_z2_tile_v1_53.sdk 为工作区，open_workspace.bat 打开，build_ethernet.py 完整构建，rebuild_ethernet_app.py 仅重建固件。
- 下载：.sdk/program_ethernet.bat；启动：根目录“启动以太网工作站.bat”。
- 报告：docs/Tile_V1.7_无损传输优化报告.md；证据：reports/v132；交付哈希：DELIVERY_MANIFEST.json。
- 默认只预览，不自动留图；真实照片运动参数 89/45。不要同时启动旧工作站或播放器。
- 实板测试：scripts/board_v17_transport.py、board_v17_continuous.py、audit_v17_motion.py。

两张真实瓷砖图传输量减少约 72%，请求耗时约 68 → 61 ms。全噪声回退仍有尝试编码的开销；高速居中和检测泛化限制详见报告。界面保留原始传输对照。
''',encoding='utf-8')
print('V1.7 report, README and verification page generated')
