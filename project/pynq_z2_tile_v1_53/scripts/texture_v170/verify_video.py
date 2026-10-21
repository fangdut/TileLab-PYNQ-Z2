"""Check the actual saved BD maps for both PS and autonomous PL masters."""
from pathlib import Path
import json

def verify(hardware):
    path=Path(hardware)/'texture_v170.srcs/sources_1/bd/system/system.bd'
    addressing=json.loads(path.read_text())['design']['addressing']
    if '/pipeline' not in addressing:return {'video':False}
    expected={'SEG_identity_Reg':0x41200000,'SEG_infer_Reg':0x43c10000,'SEG_video_regs_reg0':0x43c20000}
    for owner,space in [('/ps7','Data'),('/pipeline','m_axi_control')]:
        segments=addressing[owner]['address_spaces'][space]['segments']
        for name,offset in expected.items():
            if int(segments[name]['offset'],16)!=offset:raise ValueError(f'Wrong {owner}/{space}/{name} mapping')
    for space,segment in [('m_axi_capture','SEG_ps7_HP1_DDR_LOWOCM'),('m_axi_result','SEG_ps7_HP0_DDR_LOWOCM')]:
        item=addressing['/pipeline']['address_spaces'][space]['segments'][segment]
        if int(item['offset'],16)!=0 or item['range']!='512M':raise ValueError('Incorrect video DDR mapping')
    return {'video':True,'ps_and_pl_control_maps_match':True,'capture_hp1_result_hp0':True}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('hardware',type=Path);a=p.parse_args();print(json.dumps(verify(a.hardware)))
