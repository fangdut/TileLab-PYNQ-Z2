from pathlib import Path
R=Path(__file__).resolve().parents[1];p=R/'host/workstation.html';s=p.read_text(encoding='utf-8')
old=":'未提供 FPGA 整帧 CRC'}。"
new=":'未提供 FPGA 整帧 CRC'} · ${wf.header_crc_verified?'帧号/坐标校验已通过':'未提供响应头校验'}。"
assert s.count(old)==1;s=s.replace(old,new)
old=r'\n原图文件 SHA256 ${r.image_sha256}'
new=r'\n帧号/产品号/坐标传输校验 ${r.header_crc_verified===true?"已验证":"历史数据未提供"}\n原图文件 SHA256 ${r.image_sha256}'
assert s.count(old)==1;p.write_text(s.replace(old,new),encoding='utf-8')
(R/'host/benchmark.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>TileLab V1.12 正在验收</title><style>body{font:18px/1.8 system-ui;max-width:850px;margin:60px auto;background:#edf4f4;color:#173e47}</style><a href="/">返回工作台</a><h1>V1.12 响应头校验：验收进行中</h1><p>像素 CRC 沿用已验证的 FPGA V1.11，新版增加 Vitis 响应头 CRC，尚未完成实板验收。</p><p>最终测试报告完成后会替换本页；旧 V1.11 已单独保留并备份。</p></html>''',encoding='utf-8')
