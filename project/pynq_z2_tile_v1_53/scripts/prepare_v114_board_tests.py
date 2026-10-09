from pathlib import Path
R=Path(__file__).resolve().parents[1]
assert not (R/'scripts/board_v114_transport.py').exists()
for name in ('transport','recovery','station','background','restart'):
    s=(R/f'scripts/board_v113_{name}.py').read_text(encoding='utf-8').replace('0x10d00','0x10e00').replace('V1.13','V1.14')
    s=s.replace("and c.last_timing['header_crc_verified']", "and c.last_timing['header_crc_verified'] and c.last_timing['descriptor_crc_verified']")
    s=s.replace("and e['header_crc_verified']", "and e['header_crc_verified'] and e['descriptor_crc_verified']")
    s=s.replace("and rows[0]['header_crc_verified']", "and rows[0]['header_crc_verified'] and rows[0]['descriptor_crc_verified']")
    s=s.replace("and record['header_crc_verified']", "and record['header_crc_verified'] and record['descriptor_crc_verified']")
    s=s.replace("and f['header_crc_verified']", "and f['header_crc_verified'] and f['descriptor_crc_verified']")
    s=s.replace("('gaps','invalid','dropped','ack_errors')", "('gaps','invalid','dropped','ack_errors','descriptor_crc_errors')")
    s=s.replace("('gaps','dropped','invalid','ack_errors')", "('gaps','dropped','invalid','ack_errors','descriptor_crc_errors')")
    if name in ('transport','recovery'):
        needle="assert after['gaps']==before['gaps']"
        s=s.replace(needle,"assert after['descriptor_crc_errors']==before['descriptor_crc_errors'] and after['descriptor_verified_frames']==after['captured']\n  "+needle if name=='transport' else "assert after['descriptor_crc_errors']==before['descriptor_crc_errors'] and after['descriptor_verified_frames']==after['captured']\n        "+needle)
    (R/f'scripts/board_v114_{name}.py').write_text(s,encoding='utf-8')
for old,new in (('audit_v113_station.py','audit_v114_station.py'),('prepare_v113_ui_restart.py','prepare_v114_ui_restart.py'),('audit_v113_ui_restart.py','audit_v114_ui_restart.py')):
    s=(R/'scripts'/old).read_text(encoding='utf-8').replace('pynq_z2_tile_v1_13','pynq_z2_tile_v1_53').replace('V1.13','V1.14').replace('board_v113_restart.py','board_v114_restart.py')
    (R/'scripts'/new).write_text(s,encoding='utf-8')
s=(R/'scripts/switch_from_v112.ps1').read_text().replace('pynq_z2_tile_v1_12','pynq_z2_tile_v1_13').replace('V1.12','V1.13');(R/'scripts/switch_from_v113.ps1').write_text(s)
print('V1.14 board acceptance prepared: all three CRC proofs and descriptor counters')
