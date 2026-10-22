from pathlib import Path
import sys,json,copy,hashlib
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
sys.path.insert(0,str(P/'scripts/texture_v170'));from verify_memory_layout import verify
out=W/'v180_memory_checks01';out.mkdir(exist_ok=False)
positive=[verify(W/'v179_hw01','shared'),verify(W/'v173_hw02','split')]
relative=Path('texture_v170.srcs/sources_1/bd/system/system.bd');original=json.loads((W/'v179_hw01'/relative).read_text())
tests=[]
for case in ['wrong_hp','wrong_clock','wrong_master_count']:
    fixture=out/case;target=fixture/relative;target.parent.mkdir(parents=True)
    saved=copy.deepcopy(original);d=saved['design']
    if case=='wrong_hp':
        for net in d['interface_nets'].values():
            if 'memory_fabric/M00_AXI' in net['interface_ports']:net['interface_ports']=['memory_fabric/M00_AXI','ps7/S_AXI_HP3']
    elif case=='wrong_clock':
        for net in d['nets'].values():
            if 'ps7/S_AXI_HP0_ACLK' in net.get('ports',[]):net['ports'].remove('ps7/S_AXI_HP0_ACLK')
        d['nets']['wrong_clock_fixture']={'ports':['ps7/FCLK_CLK1','ps7/S_AXI_HP0_ACLK']}
    else:d['components']['memory_fabric']['parameters']['NUM_SI']['value']='4'
    target.write_text(json.dumps(saved))
    try:verify(fixture,'shared')
    except ValueError as e:tests.append(dict(case=case,rejected=True,error=str(e)))
    else:raise AssertionError('Invalid layout accepted: '+case)
try:verify(W/'v179_hw01','split')
except ValueError as e:tests.append(dict(case='requested_split_but_shared',rejected=True,error=str(e)))
else:raise AssertionError('Requested layout mismatch accepted')
j=dict(scope='READ_ONLY_BD_CHECKER_POSITIVE_AND_NEGATIVE_FIXTURES_NOT_NEW_HARDWARE',passed=True,positive=positive,negative=tests,checker_sha256=hashlib.sha256((P/'scripts/texture_v170/verify_memory_layout.py').read_bytes()).hexdigest())
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
