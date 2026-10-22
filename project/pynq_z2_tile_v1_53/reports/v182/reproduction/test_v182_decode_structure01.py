from pathlib import Path
import sys,json,shutil,hashlib,xml.etree.ElementTree as ET
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
sys.path.insert(0,str(P/'tools/fpga_texture_v170'));from check_operation_decode import inspect
out=W/'v182_decode_structure_negative01';out.mkdir(exist_ok=False);positive=inspect(W/'v170_hls64');assert positive['passed'] and inspect(W/'v170_hls62') is None
files=['src/texture_integer.cpp','solution/syn/verilog/texture_integer.v','solution/syn/verilog/texture_integer_decode_operation.v','solution/syn/report/decode_operation_csynth.xml'];negative=[]
for case in ['wrong_port_width','missing_comparison_stage','wrong_latency']:
    folder=out/case
    for name in files:p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(W/'v170_hls64'/name,p)
    rtl=folder/'solution/syn/verilog/texture_integer_decode_operation.v';text=rtl.read_text()
    if case=='wrong_port_width':assert 'output  [2:0] ap_return;' in text;rtl.write_text(text.replace('output  [2:0] ap_return;','output  [31:0] ap_return;'))
    elif case=='missing_comparison_stage':
        line=next(l for l in text.splitlines() if '_pp0_iter1_reg <=' in l);rtl.write_text(text.replace(line,''))
    else:
        xml=folder/'solution/syn/report/decode_operation_csynth.xml';doc=ET.parse(xml);doc.find('./PerformanceEstimates/SummaryOfOverallLatency/Best-caseLatency').text='0';doc.write(xml)
    try:inspect(folder)
    except ValueError as e:negative.append(dict(case=case,rejected=True,error=str(e)))
    else:raise AssertionError('Invalid decoder structure accepted: '+case)
j=dict(scope='STATIC_HLS_STRUCTURE_POSITIVE_AND_MUTATED_FIXTURES_NOT_RTL_SIMULATION',passed=True,positive=positive,negative=negative,checker_sha256=hashlib.sha256((P/'tools/fpga_texture_v170/check_operation_decode.py').read_bytes()).hexdigest())
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
