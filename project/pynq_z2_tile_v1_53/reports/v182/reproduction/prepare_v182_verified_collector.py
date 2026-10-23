from pathlib import Path
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');s=(W/'collect_v180_verified.py').read_text()
for a,b in [('physical V180 run','physical V182 run'),("run=W/'v180_acceptance01';hw=W/'v180_hw01';dst=P/'reports/v180/verified_hdmi_split125'","run=W/'v182_acceptance01';hw=W/'v182_hw01';dst=P/'reports/v182/verified_hdmi_control125'"),("W/'v180_physical_pipeline01.json'","W/'v182_physical_pipeline01.json'"),("W/'v170_hls62/src/texture_integer.cpp'","W/'v170_hls65/src/texture_integer.cpp'"),("W/'v179_all_c05/summary.json'","W/'v182_all_c01/summary.json'"),('v180_transport_stress01','v182_transport_stress01'),('after_v180_video','after_v182_video')]:
    assert a in s,a;s=s.replace(a,b)
out=W/'collect_v182_verified.py';assert not out.exists();out.write_text(s);compile(s,str(out),'exec');print('V182_COLLECTOR_PREPARED_NOT_EXECUTED_REQUIRES_ACTUAL_PHYSICAL_ACCURACY_SPEED_PASS')
