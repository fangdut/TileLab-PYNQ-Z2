from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=R/'scripts/board_v17_transport.py';s=p.read_text()
s=s.replace('0x10700','0x10800')
s=s.replace("assert all(r['compact']['wire_payload_bytes']<=FRAME_BYTES for r in rows)","assert all(r['compact']['wire_payload_bytes']<=FRAME_BYTES for r in rows)\n  assert after['compression_probe_bypasses']-before['compression_probe_bypasses']>=10,'Noise did not use probe bypass'")
(R/'scripts/board_v18_transport.py').write_text(s)
(R/'scripts/board_v18_continuous.py').write_text((R/'scripts/board_v17_continuous.py').read_text())
(R/'scripts/audit_v18_motion.py').write_text((R/'scripts/audit_v17_motion.py').read_text().replace('board_v17_continuous','board_v18_continuous'))
p=R/'scripts/switch_from_v16.ps1';s=p.read_text().replace('v1_6','v1_7').replace('V1.6','V1.7')
(R/'scripts/switch_from_v17.ps1').write_text(s)
