from pathlib import Path
R=Path(__file__).resolve().parents[1]
files=['board_v114_transport.py','board_v114_recovery.py','board_v114_restart.py','board_v114_station.py','board_v114_background.py','board_v114_descriptor_fault.py','audit_v114_station.py','audit_v114_ui_restart.py','prepare_v114_ui_restart.py']
for name in files:
 p=R/'scripts'/name;s=p.read_text().replace('v114','v115').replace('0x10e00','0x10f00')
 (p.parent/name.replace('v114','v115')).write_text(s,encoding='utf-8')
p=R/'scripts/inject_descriptor_fault.tcl';s=p.read_text().replace('0x10e00','0x10f00');p.write_text(s,encoding='utf-8')
p=R/'scripts/switch_from_v113.ps1';s=p.read_text().replace('v1_13','v1_14').replace('V1.13','V1.14');(p.parent/'switch_from_v114.ps1').write_text(s,encoding='utf-8')
s=(R/'scripts/verify_v114_hardware.tcl').read_text().replace('crc_index_reg* &&','trailer_index_reg* &&')
s=s.replace('if {[llength $crc_cells]!=32 || [llength $index_cells]!=6}', 'set removed_index [get_cells -quiet -hier -filter {NAME =~ *crc_index_reg* && REF_NAME =~ FD*}]\nif {[llength $crc_cells]!=32 || [llength $index_cells]!=6 || [llength $removed_index]!=0}')
s=s.replace('Expected 32 shared CRC state bits and 6 metadata index bits','Expected 32 CRC bits, 6 shared descriptor-index bits, and no separate CRC-index registers')
(R/'scripts/verify_v115_hardware.tcl').write_text(s,encoding='utf-8')
print('V1.15 acceptance uses 0x10f00 firmware and checks the removed duplicate index')
