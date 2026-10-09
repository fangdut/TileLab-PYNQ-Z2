from pathlib import Path
R=Path(__file__).resolve().parents[1]
assert not (R/'scripts/board_v113_transport.py').exists()
for name in ('transport','recovery','station','background'):
    text=(R/f'scripts/board_v112_{name}.py').read_text(encoding='utf-8').replace('0x10c00','0x10d00')
    if name=='recovery':
        text=text.replace("assert ops.count(1)==1 and ops.count(2)>=2", "assert ops.count(1)==1 and ops.count(2)==1 and ops.count(3)>=2\n                assert s.records.confirmations.history()[0]['status']=='ALREADY_ACKNOWLEDGED'")
    (R/f'scripts/board_v113_{name}.py').write_text(text,encoding='utf-8')
(R/'scripts/audit_v113_station.py').write_text((R/'scripts/audit_v112_station.py').read_text(encoding='utf-8'),encoding='utf-8')
text=(R/'scripts/switch_from_v111.ps1').read_text().replace('pynq_z2_tile_v1_11','pynq_z2_tile_v1_12').replace('V1.11','V1.12')
(R/'scripts/switch_from_v112.ps1').write_text(text)
print('V1.13 board tests prepared; lost ACK now reconciles via status without repeated ACK')
