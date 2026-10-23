"""Bind bounded row addressing to actual generated, pipelined HLS structure."""
from pathlib import Path
import argparse,hashlib,json,re,xml.etree.ElementTree as ET

def inspect(hls):
    hls=Path(hls);source=hls/'src/texture_integer.cpp';code=source.read_text()
    if 'static ap_uint<21> row_offset(' not in code:return None
    guard='if(h[0]!=0x17000001||!width||!height||width>1024||height>1024||side<8||side>224'
    calls=['row0_offset=row_offset(ap_uint<10>(y0),ap_uint<11>(width));',
           'row1_offset=row_offset(ap_uint<10>(y1),ap_uint<11>(width));']
    if guard not in code or any(t not in code or code.index(t)<code.index(guard) for t in calls):
        raise ValueError('Original size validation must precede both narrowed row offsets')
    if 'rgb[y0*width+x]' in code or 'rgb[y1*width+x]' in code:
        raise ValueError('Old wide row expression remains')
    root=hls/'solution/syn';rtl=root/'verilog/texture_integer_row_offset.v';text=rtl.read_text()
    for pattern in [r'input\s+\[9:0\]\s+row\s*;',r'input\s+\[10:0\]\s+width\s*;',r'output\s+\[20:0\]\s+ap_return\s*;']:
        if not re.search(pattern,text):raise ValueError('Generated row helper widths changed')
    xml=root/'report/row_offset_csynth.xml';r=ET.parse(xml).getroot();latency=r.find('./PerformanceEstimates/SummaryOfOverallLatency')
    if latency.findtext('Best-caseLatency')!='3' or latency.findtext('Worst-caseLatency')!='3' or latency.findtext('Interval-min')!='1':
        raise ValueError('Expected row helper latency3 and II1')
    if r.findtext('./AreaEstimates/Resources/DSP')!='1':raise ValueError('Expected one row multiplier DSP estimate')
    mul=root/'verilog/texture_integer_mul_11ns_10ns_21_4_0.v';m=mul.read_text()
    for pattern in [r'din0_reg\s*<=\s*din0\s*;',r'din1_reg\s*<=\s*din1\s*;',
                    r'buff0\s*<=\s*tmp_product\s*;',r'buff1\s*<=\s*buff0\s*;']:
        if not re.search(pattern,m):raise ValueError('Input/multiply/output register stage missing')
    top=root/'verilog/texture_integer.v';t=top.read_text()
    if len(re.findall(r'\btexture_integer_row_offset\s+\w+\s*\(',t))!=1:
        raise ValueError('Expected one shared row helper in detector')
    if any('mul_22s_32s_32' in p.read_text() for p in (root/'verilog').glob('*.v')):
        raise ValueError('Measured old22x32 multiplier still generated')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(scope='GENERATED_ROW_ADDRESS_STRUCTURE_NOT_FULL_RTL_TIMING_OR_BOARD',passed=True,
        source_sha256=sha(source),helper_rtl_sha256=sha(rtl),multiplier_rtl_sha256=sha(mul),
        helper_report_sha256=sha(xml),top_rtl_sha256=sha(top),row_bits=10,width_bits=11,output_bits=21,
        latency_cycles=3,initiation_interval=1,estimated_helper_dsp=1,
        original_input_validation_before_narrowing=True,old22x32_multiplier_removed=True,
        interpretation='Width/resource checks are generated-HLS evidence; actual DSP placement/timing and production-frame performance remain unmeasured.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=inspect(a.hls)
    if result is None:raise ValueError('No bounded row helper in candidate')
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
