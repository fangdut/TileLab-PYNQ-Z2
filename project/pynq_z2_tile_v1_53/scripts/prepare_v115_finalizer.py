from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=(R.parent/'pynq_z2_tile_v1_14/scripts/finalize_v114.py').read_text(encoding='utf-8')
s=s.replace('v114','v115').replace('V1.14','V1.15').replace('v1_14','v1_15').replace('v1_13','v1_14').replace('0x10e00','0x10f00')
s=s.replace('descriptor_validation_summary.json','shared_port_validation_summary.json').replace('V1.15_描述校验与实板报告','V1.15_读取通路优化与实板报告')
s=s.replace('BOARD_VALIDATED_PL_DESCRIPTOR_CRC_WITH_KNOWN_LIMITS','BOARD_VALIDATED_SHARED_DESCRIPTOR_PORT_WITH_KNOWN_LIMITS')
s=s.replace('V1.15 full-frame pixel and PL descriptor CRC','V1.15 shared descriptor read port plus pixel/descriptor CRC')
marker="native=read(R/'reports/v132/descriptor_native.json')"
assert marker in s
s=s.replace(marker,"assert summary['optimization']['passed'] and summary['random_equivalence']['passed']\nassert sha(R/'rtl/frame_capture_sg.v')==summary['optimization']['optimized_rtl_sha256']==summary['random_equivalence']['optimized_rtl_sha256']\nassert summary['resources']['Slice LUTs']<17503\n"+marker)
s=s.replace("'reports/v132/hardware_crc_check.json']","'reports/v132/hardware_crc_check.json','reports/v132/capture_optimization.json','reports/v132/random_equivalence.json']")
(R/'scripts/finalize_v115.py').write_text(s,encoding='utf-8')
print('V1.15 finalizer requires full actual-board evidence, lower implemented LUT count, and matching RTL hashes')
