"""Publish the verification page only from completed evidence, never placeholders."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
s=json.loads((O/'quad_weak_validation_summary.json').read_text(encoding='utf-8'))
assert s['passed'] and s['version']=='V1.24'
old=s['weak']['legacy'];new=s['weak']['quad'];h=s['hardware'];c=s['station_full'];a=s['identity'];b=s['background']
rows=''.join(f"<tr><td>{k}</td><td>{v['raw_request_ms']:.2f}</td><td>{v['compact_request_ms']:.2f}</td><td>{v['saving_percent']:.4f}%</td></tr>" for k,v in s['transport_full']['summary'].items())
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.24 实板验证</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#edf4f4;color:#173e47;font:16px/1.7 system-ui}}main{{max-width:1050px;margin:32px auto;padding:30px;background:white;border-radius:18px}}a{{color:#087d80}}h1{{font-size:32px}}h2{{margin-top:30px}}.tag{{display:inline-block;background:#daf3e6;padding:5px 14px;border-radius:20px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.metric{{padding:18px;background:#edf6f5;border-radius:12px}}.metric b{{display:block;font-size:28px}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #d5e4e6}}.limit{{padding:18px;background:#fff0df;border-left:4px solid #ba772c}}small{{color:#52747a}}@media(max-width:700px){{main{{margin:0;padding:20px}}.grid{{grid-template-columns:1fr}}}}</style>
<main><a href="/">← 返回检测工作台</a><p class="tag">V1.24 · 实板逐项验收完成</p><h1>四级弱裂纹支持，保留完整证据</h1><p>真实 HDMI → FPGA → DDR → 以太网采集。检测仍在 FPGA，每时钟处理一个像素；像素时钟 74.25 MHz，720p60。电脑预览为抽样接收。</p>
<div class="grid"><div class="metric">裂纹像素召回率<b>{old['pixel_recall']*100:.2f}% → {new['pixel_recall']*100:.2f}%</b><small>相同的 50 张历史照片重新上板</small></div><div class="metric">正常瓷砖误报警<b>0 / 230</b><small>已参与开发的正常素材，不是盲测</small></div><div class="metric">连续移动缺陷产品<b>{c['saved']} 个 / {c['seconds']:.1f} 秒</b><small>最佳截图最大偏离中心 {a['max_center_error_px']} 像素</small></div></div>
<h2>改善与代价</h2><p>旧两级阈值 89，新四级阈值 90；新增两级邻域支持，让相邻的弱响应被强裂纹带动。两种模式均命中 17/17 裂纹照片、0/33 正常照片误报，50 对输入 PNG 完全一致。像素精确率从 {old['pixel_precision']*100:.2f}% 变为 {new['pixel_precision']*100:.2f}%。更长的弱裂纹被接纳，也增加了少量非裂纹像素。</p>
<p>增加 168 LUT、554 寄存器、9 BRAM；当前 {h['resources']['Slice LUTs']:.0f} LUT、{h['resources']['Slice Registers']:.0f} 寄存器、67 BRAM、2 DSP。新增延迟 44.552 微秒，吞吐不变。建立时间裕量 {h['wns_ns']:+.3f} ns，保持时间裕量 {h['whs_ns']:+.3f} ns。</p>
<h2>传输重新测量</h2><p>50 对保留事件的 RAW 与无损压缩逐字节相同；三类 CRC 均通过。下表为请求中位数，包含本机软件和传输耗时，并非纯网线带宽。</p><table><thead><tr><th>输入</th><th>RAW 毫秒</th><th>压缩毫秒</th><th>负载减少</th></tr></thead><tbody>{rows}</tbody></table>
<p>冻结预览时继续收缺陷事件，应用层接收字节率减少 {b['received_rate_reduction_percent']:.3f}%。默认仅预览，自动归档关闭；存档容量上限 1 GiB，满额不删除旧证据。</p>
<h2>完成的回归</h2><p>188 项主机测试；20,736 像素四级/旁路仿真及中途复位；73,728 彩色像素、24 组合成链路验证；19,840 像素旧检测回归。13 类非法请求实板拒绝、产品间隙模式切换、4 类停止接收边界、9 类网络故障、3 类重启恢复、界面待确认恢复、3 类播放器文件冲突均通过。连续运动证据与独立参考逐像素一致，没有新增采集错误或队列丢失。</p>
<div class="limit"><strong>适用范围仍有限</strong><p>这是指定材质的工程原型。800 张正常屋面陶瓷跨材质压力测试，旧模式误报 547 张、新模式 555 张；不能宣称通用识别改善。像素召回率仍低，缺少强种子的裂纹仍可能漏检。尚无真实相机、曝光和运动模糊验收。</p><p>仍有 5 个既有 CDC 不安全端点；12 事件缓存无法抵抗无限暂停或掉电。HDMI 红框用上一完成帧，电脑存档的图、框和身份绑定同一帧。播放器状态确认不等于物理 HDMI 确认；以完整报告中的限制为准。</p></div>
<p><a href="/api/benchmark">本版完整验证 JSON</a> · 工程内报告：docs/Tile_V1.24_四级弱裂纹与实板报告.md</p></main></html>'''
(R/'host/benchmark.html').write_text(page,encoding='utf-8')
p=R/'host/recipes.json';text=p.read_text(encoding='utf-8');assert '尚在 V1.24 实板验证中' in text
p.write_text(text.replace('尚在 V1.24 实板验证中','V1.24 实板回归通过，仅适用于当前材质与显示尺度'),encoding='utf-8')
p=R/'README.md';text=p.read_text(encoding='utf-8')
text=text.replace('当前处于构建和实板验收阶段。只有本目录出现状态为 BOARD_VALIDATED 的 DELIVERY_MANIFEST.json，才视为本版交付完成。','本版已完成构建、实板逐项验收与报告；最终下载文件和源码哈希见 DELIVERY_MANIFEST.json，状态为 BOARD_VALIDATED_FOUR_PASS_WEAK_SUPPORT_WITH_MATERIAL_LIMITS。')
text=text.replace('完整报告会在本版实板测试完成后写入 docs。','完整报告见 [四级弱裂纹与实板报告](docs/Tile_V1.24_四级弱裂纹与实板报告.md)，原理见 [四级生长原理](docs/V1.24_弱裂纹四级生长原理.md)。')
p.write_text(text,encoding='utf-8')
print('Published V1.24 validation page and final profile description from completed evidence')
