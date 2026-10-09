from pathlib import Path
p=Path(__file__).resolve().parents[1]/'host/workstation.html'
s=p.read_text(encoding='utf-8')
old=r'\nSHA256 ${r.image_sha256}'
new=r'\nFPGA 整帧 CRC ${r.pixel_crc_verified===true?"已验证 0x"+r.pixel_crc32.toString(16).padStart(8,"0"):"历史数据未提供"}\n原图文件 SHA256 ${r.image_sha256}'
assert s.count(old)==1
p.write_text(s.replace(old,new),encoding='utf-8')
