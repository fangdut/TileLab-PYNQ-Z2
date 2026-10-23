"""Bind optional exact quarter interpolation to actual registered HLS units."""
from pathlib import Path
import argparse,hashlib,json,re,xml.etree.ElementTree as ET

def inspect(hls):
    hls=Path(hls);source=hls/'src/texture_integer.cpp';code=source.read_text()
    if 'static ap_int<12> quarter_horizontal(' not in code:return None
    required=['top=quarter_horizontal(a,b,fx),bottom=quarter_horizontal(c,d,fx);',
              'total=quarter_vertical(top,bottom,fy);',
              'int v=total;return i8(v<0?-((-v+8)>>4):((v+8)>>4));']
    if any(t not in code for t in required):raise ValueError('Interpolation call graph or signed rounding changed')
    root=hls/'solution/syn';top=root/'verilog/texture_integer.v';text=top.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();units={}
    for name,ports in [('quarter_horizontal',{'a':8,'b':8,'f':2,'ap_return':12}),('quarter_vertical',{'top':12,'bottom':12,'f':2,'ap_return':16})]:
        rtl=root/'verilog'/('texture_integer_'+name+'.v');r=rtl.read_text()
        for port,bits in ports.items():
            direction='output' if port=='ap_return' else 'input'
            if not re.search(r'\b'+direction+r'\s+\['+str(bits-1)+r':0\]\s+'+port+r'\s*;',r):
                raise ValueError('Generated quarter port width changed: '+name+'/'+port)
        xml=root/'report'/(name+'_csynth.xml');report=ET.parse(xml).getroot();latency=report.find('./PerformanceEstimates/SummaryOfOverallLatency')
        if latency.findtext('Best-caseLatency')!='2' or latency.findtext('Worst-caseLatency')!='2' or latency.findtext('Interval-min')!='1':
            raise ValueError('Expected each quarter stage latency2/II1')
        if report.findtext('./AreaEstimates/Resources/DSP')!='0':raise ValueError('Quarter stage consumes new DSPs')
        count=len(re.findall(r'\btexture_integer_'+name+r'\s+\w+\s*\(',text))
        if count!=16:raise ValueError('Expected16 parallel quarter stage instances: '+name)
        if 'always @ (posedge ap_clk)' not in r:raise ValueError('Clocked quarter registers missing')
        units[name]=dict(rtl_sha256=sha(rtl),report_sha256=sha(xml),latency_cycles=2,initiation_interval=1,estimated_dsp=0,instances=count)
    return dict(scope='GENERATED_QUARTER_REGISTERED_STRUCTURE_NOT_FULL_RTL_TIMING_OR_BOARD',passed=True,
        source_sha256=sha(source),top_rtl_sha256=sha(top),units=units,
        interpretation='HLS latency/register structure is source-bound; routed timing, actual resource use and board speed still require separate acceptance.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=inspect(a.hls)
    if r is None:raise ValueError('No registered quarter stages in candidate')
    a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
