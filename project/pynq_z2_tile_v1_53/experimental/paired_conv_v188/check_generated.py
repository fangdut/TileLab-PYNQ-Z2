"""Conservative structural gates for paired convolution. RTL simulation still required."""
from pathlib import Path
import argparse,hashlib,json,re,xml.etree.ElementTree as ET
def inspect(hls):
    src=hls/'src/texture_integer.cpp';code=src.read_text()
    assert 'i32 acc[CO][32];' in code and 'CO=32,CRD=128' in code
    assert 'int span=(!nearest&&depth)?DW_SPAN:32;' in code
    reuse=min(32,int(re.search(r'DW_SPAN=(\d+)',code)[1]))
    files=[p for p in (hls/'solution/syn/verilog').glob('*mac_row_Pipeline*.v') if 'acc_ce0_local' in p.read_text()]
    assert len(files)==1
    rtl=files[0];text=rtl.read_text();ports={}
    for block in text.split('always @ (*) begin')[1:]:
        block=block.split('always @',1)[0]
        m=re.search(r"(acc(?:_\d+)?)_(ce0|we1)_local = 1'b1;",block)
        if not m:continue
        stages={int(n) for n in re.findall(r'ap_enable_reg_pp0_iter(\d+)',block[:m.start()])}
        assert len(stages)==1,(m[0],stages)
        ports.setdefault(m[1],{})[m[2]]=stages.pop()
    assert len(ports)==32,len(ports)
    rows=[]
    for name,stages in sorted(ports.items()):
        assert set(stages)=={'ce0','we1'}
        delta=stages['we1']-stages['ce0']
        rows.append(dict(bank=name,read_stage=stages['ce0'],write_stage=stages['we1'],delta=delta,safe=0<=delta<reuse))
    area=ET.parse(hls/'solution/syn/report/texture_integer_csynth.xml').getroot().find('AreaEstimates/Resources')
    resources={e.tag:int(e.text) for e in area}
    dot=list((hls/'solution/syn/report').glob('dot128*_csynth.xml'));assert len(dot)==1
    dot_area=ET.parse(dot[0]).getroot().find('AreaEstimates/Resources')
    dot_resources={e.tag:int(e.text) for e in dot_area}
    return dict(scope='PAIRED_GENERATED_STATIC_GATES_NOT_RTL_OR_BOARD',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),rtl_sha256=hashlib.sha256(rtl.read_bytes()).hexdigest(),resources=resources,dot_resources=dot_resources,minimum_reuse_iterations=reuse,recurrence=rows,recurrence_safe=all(x['safe'] for x in rows),shared_dot_128_dsp=dot_resources['DSP']==128,capacity_gate=resources['DSP']<=215 and resources['BRAM_18K']<=276,capacity_note='Reserve at least5 DSP and4 BRAM18 for surrounding video design. HLS LUT/FF estimates are not routed utilization.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=inspect(a.hls);r['passed']=r['recurrence_safe'] and r['shared_dot_128_dsp'] and r['capacity_gate'];a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='recurrence'}));raise SystemExit(0 if r['passed'] else 2)
