"""Check the actual saved BD maps for both PS and autonomous PL masters."""
from pathlib import Path
import json,re


def verify_bus_skew_report(path):
    proof=Path(path).read_text()
    if 'VIOLATED' in proof.upper():raise ValueError('Asynchronous FIFO bus skew failed')
    if len(re.findall(r'Slack\s+\(MET\)',proof))<2 or any(
        name not in proof for name in ['rd_pntr_cdc_inst/src_gray_ff_reg','wr_pntr_cdc_inst/src_gray_ff_reg']):
        raise ValueError('Read and write FIFO Gray-bus skew constraints must both be present and pass')
    return {'read_and_write_gray_bus_skew_passed':True}

def verify(hardware):
    path=Path(hardware)/'texture_v170.srcs/sources_1/bd/system/system.bd'
    design=json.loads(path.read_text())['design'];addressing=design['addressing']
    if '/pipeline' not in addressing:return {'video':False}
    expected={'SEG_identity_Reg':0x41200000,'SEG_infer_Reg':0x43c10000,'SEG_video_regs_reg0':0x43c20000}
    for owner,space in [('/ps7','Data'),('/pipeline','m_axi_control')]:
        segments=addressing[owner]['address_spaces'][space]['segments']
        for name,offset in expected.items():
            if int(segments[name]['offset'],16)!=offset:raise ValueError(f'Wrong {owner}/{space}/{name} mapping')
    split='work_fabric' in design['components']
    result_hp=3 if split else 0
    for space,segment in [('m_axi_capture','SEG_ps7_HP1_DDR_LOWOCM'),('m_axi_result',f'SEG_ps7_HP{result_hp}_DDR_LOWOCM')]:
        item=addressing['/pipeline']['address_spaces'][space]['segments'][segment]
        if int(item['offset'],16)!=0 or item['range']!='512M':raise ValueError('Incorrect video DDR mapping')
    for name,hp in [('workmem',0),('modelmem',2 if split else 0),('inputmem',result_hp),('outmem',result_hp)]:
        segments=addressing['/infer']['address_spaces']['Data_m_axi_'+name]['segments']
        expected='SEG_ps7_HP'+str(hp)+'_DDR_LOWOCM'
        if set(segments)!={expected} or int(segments[expected]['offset'],16)!=0 or segments[expected]['range']!='512M':
            raise ValueError('Incorrect inference DDR mapping: '+name)
    return {'video':True,'ps_and_pl_control_maps_match':True,'memory_layout':'split' if split else 'shared',
            'capture_hp':1,'result_hp':result_hp,'all_inference_ddr_maps_verified':True}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('hardware',type=Path);a=p.parse_args();print(json.dumps(verify(a.hardware)))
