from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=R/'host/workstation.py';s=p.read_text(encoding='utf-8').replace('1.14.0-iteration','1.14.0-pl-descriptor-integrity').replace('reports/v132/journal_validation_summary.json','reports/v132/descriptor_validation_summary.json');p.write_text(s,encoding='utf-8')
p=R/'host/workstation.html';s=p.read_text(encoding='utf-8')
old="${wf.header_crc_verified?'帧号/坐标校验已通过':'未提供响应头校验'}。"
assert old in s
s=s.replace(old,old[:-1]+" · ${wf.descriptor_crc_verified?'PL 描述校验已通过':'未提供 PL 描述校验'}。")
old=r'\n原图文件 SHA256 ${r.image_sha256}'
assert old in s
s=s.replace(old,r'\nPL → ARM 描述校验 ${r.descriptor_crc_verified?"固件已核对 FPGA 校验值":"历史数据未提供"}'+old)
p.write_text(s,encoding='utf-8')
print('V1.14 UI distinguishes PL descriptor validation from header and pixel CRCs')
