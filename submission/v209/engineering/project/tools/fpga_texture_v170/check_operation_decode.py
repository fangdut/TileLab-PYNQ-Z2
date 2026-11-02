"""Bind the optional registered opcode decoder to generated HLS structure."""
from pathlib import Path
import argparse,hashlib,json,re,xml.etree.ElementTree as ET

def inspect(hls):
    hls=Path(hls);source=hls/'src/texture_integer.cpp';code=source.read_text()
    if 'static ap_uint<3> decode_operation(' not in code:return None
    for token in ['if(raw==1)flags=1;','else if(raw==2)flags=2;','else if(raw==3)flags=4;',
                  'operation=decode_operation(t[0]);','bool(operation[1])']:
        if token not in code:raise ValueError('Unsupported opcode decode implementation')
    if len(re.findall(r'\bt\[0\]',code))!=1:raise ValueError('Raw opcode still used outside the decoder')
    root=hls/'solution/syn';rtl=root/'verilog/texture_integer_decode_operation.v';text=rtl.read_text()
    if not re.search(r'input\s+\[31:0\]\s+raw\s*;',text) or not re.search(r'output\s+\[2:0\]\s+ap_return\s*;',text):
        raise ValueError('Generated decoder no longer32-input/3-output')
    registers=re.findall(r'(icmp_\w+_pp0_iter1_reg)\s*<=\s*(icmp_\w+_reg_\d+)\s*;',text)
    if len(registers)!=3 or 'always @ (posedge ap_clk)' not in text:raise ValueError('Three registered comparison stages missing')
    xml=root/'report/decode_operation_csynth.xml';report=ET.parse(xml).getroot()
    latency=report.find('./PerformanceEstimates/SummaryOfOverallLatency')
    if latency.findtext('Best-caseLatency')!='2' or latency.findtext('Worst-caseLatency')!='2' or latency.findtext('Interval-min')!='1':
        raise ValueError('Decoder latency/II changed')
    top=root/'verilog/texture_integer.v';toptext=top.read_text()
    if len(re.findall(r'\btexture_integer_decode_operation\s+\w+\s*\(',toptext))!=1:
        raise ValueError('Expected one decoder instance in the full detector')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(scope='GENERATED_HLS_CONTROL_STRUCTURE_NOT_FULL_RTL_SIMULATION_OR_BOARD',passed=True,
                source_sha256=sha(source),decoder_rtl_sha256=sha(rtl),top_rtl_sha256=sha(top),decoder_report_sha256=sha(xml),
                raw_bits=32,onehot_bits=3,latency_cycles=2,initiation_interval=1,comparison_stage_pairs=registers)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=inspect(a.hls)
    if r is None:raise ValueError('No registered decoder in this candidate')
    a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
