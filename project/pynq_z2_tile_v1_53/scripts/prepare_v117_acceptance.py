from pathlib import Path
R=Path(__file__).resolve().parents[1]
for name in ['board_v116_transport.py','board_v116_recovery.py','board_v116_restart.py','board_v116_station.py','board_v116_background.py','audit_v116_station.py','audit_v116_ui_restart.py','prepare_v116_ui_restart.py']:
 p=R/'scripts'/name;s=p.read_text().replace('v116','v117').replace('V1.16','V1.17').replace('0x11000','0x11100')
 (p.parent/name.replace('v116','v117')).write_text(s,encoding='utf-8')
p=R/'scripts/switch_from_v115.ps1'
(p.parent/'switch_from_v116.ps1').write_text(p.read_text().replace('v1_15','v1_16').replace('V1.15','V1.16'),encoding='utf-8')
print('V1.17 actual-board acceptance harnesses prepared')
