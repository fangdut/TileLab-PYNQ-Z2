from pathlib import Path
R=Path(__file__).resolve().parents[1]
for name in ['board_v115_transport.py','board_v115_recovery.py','board_v115_restart.py','board_v115_station.py','board_v115_background.py','audit_v115_station.py','audit_v115_ui_restart.py','prepare_v115_ui_restart.py']:
 p=R/'scripts'/name
 s=p.read_text().replace('v115','v116').replace('V1.15','V1.16').replace('0x10f00','0x11000')
 (p.parent/name.replace('v115','v116')).write_text(s,encoding='utf-8')
p=R/'scripts/switch_from_v114.ps1'
(p.parent/'switch_from_v115.ps1').write_text(p.read_text().replace('v1_14','v1_15').replace('V1.14','V1.15'),encoding='utf-8')
print('V1.16 actual board acceptance harnesses prepared; no results inherited')
