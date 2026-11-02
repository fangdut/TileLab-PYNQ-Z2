"""Check saved DDR master/HP connections, including their actual clock nets."""
from pathlib import Path
import argparse,hashlib,json

def verify(hardware,expected=None):
    hardware=Path(hardware);bd=hardware/'texture_v170.srcs/sources_1/bd/system/system.bd'
    d=json.loads(bd.read_text())['design'];c=d['components'];ps=c['ps7']['parameters']
    layout='split' if 'work_fabric' in c or 'model_fabric' in c else 'shared'
    if expected is not None and layout!=expected:raise ValueError('Saved DDR layout differs from requested layout')
    video='pipeline' in c
    pairs=[]
    if layout=='split':
        if not all(n in c for n in ['work_fabric','model_fabric']):raise ValueError('Incomplete split DDR fabric')
        pairs += [('infer/m_axi_workmem','work_fabric/S00_AXI'),('work_fabric/M00_AXI','ps7/S_AXI_HP0'),
                  ('infer/m_axi_modelmem','model_fabric/S00_AXI'),('model_fabric/M00_AXI','ps7/S_AXI_HP2'),
                  ('infer/m_axi_inputmem','memory_fabric/S00_AXI'),('infer/m_axi_outmem','memory_fabric/S01_AXI'),
                  ('memory_fabric/M00_AXI','ps7/S_AXI_HP3')]
        hp=[0,2,3];result_si=2
        for name in ['work_fabric','model_fabric']:
            if int(c[name]['parameters']['NUM_SI']['value'])!=1:raise ValueError('Unexpected split fabric master count')
    else:
        pairs += [('infer/'+p,'memory_fabric/S%02d_AXI'%i) for i,p in enumerate(['m_axi_modelmem','m_axi_workmem','m_axi_inputmem','m_axi_outmem'])]
        pairs += [('memory_fabric/M00_AXI','ps7/S_AXI_HP0')];hp=[0];result_si=4
    if video:
        pairs += [('pipeline/m_axi_result','memory_fabric/S%02d_AXI'%result_si),('capture_fabric/M00_AXI','ps7/S_AXI_HP1')]
        hp.append(1)
    if int(c['memory_fabric']['parameters']['NUM_SI']['value'])!=result_si+int(video):raise ValueError('DDR master count disagrees with connected clients')
    nets=[set(v['interface_ports']) for v in d['interface_nets'].values()]
    for a,b in pairs:
        matches=[n for n in nets if a in n]
        if len(matches)!=1 or matches[0]!={a,b}:raise ValueError('DDR connection mismatch: '+a+' -> '+b)
    clock_ports=['infer/ap_clk','memory_fabric/aclk']+['ps7/S_AXI_HP%d_ACLK'%n for n in hp]
    if layout=='split':clock_ports += ['work_fabric/aclk','model_fabric/aclk']
    if video:clock_ports.append('capture_fabric/aclk')
    wire_nets=[set(v.get('ports',[])) for v in d['nets'].values()]
    for port in clock_ports:
        matches=[n for n in wire_nets if port in n]
        if len(matches)!=1 or 'ps7/FCLK_CLK0' not in matches[0]:raise ValueError('DDR port not on actual FCLK0 net: '+port)
    for n in hp:
        if int(ps['PCW_USE_S_AXI_HP%d'%n]['value'])!=1:raise ValueError('Connected PS HP port disabled')
    return dict(scope='SAVED_BD_DDR_CONNECTIVITY_NOT_THROUGHPUT',memory_layout=layout,video=video,
                checked_interface_pairs=pairs,enabled_hp_ports=sorted(hp),clock_ports=clock_ports,
                bd_sha256=hashlib.sha256(bd.read_bytes()).hexdigest())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('hardware',type=Path);p.add_argument('--expected',choices=['shared','split']);a=p.parse_args()
    print(json.dumps(verify(a.hardware,a.expected)))
