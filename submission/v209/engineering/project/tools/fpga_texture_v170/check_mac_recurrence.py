"""Check generated MAC RTL recurrence stages; not a substitute for co-simulation."""
from pathlib import Path
import argparse,hashlib,json,re

def inspect(hls):
    files=[p for p in (hls/'solution/syn/verilog').glob('*mac_row_Pipeline*.v') if 'acc_ce0_local' in p.read_text()]
    if len(files)!=1:raise ValueError('Expected one flattened shared MAC RTL module')
    rtl=files[0];text=rtl.read_text();source=hls/'src/texture_integer.cpp'
    code=source.read_text()
    allocation=re.search(r'(?:i32|ap_int<24>) acc\[(O|CO)\]\[(\d+)\]',code)
    if not allocation:raise ValueError('Unknown accumulator allocation')
    lanes=int(re.search(r'\b'+allocation[1]+r'=(\d+)',code)[1])
    if lanes not in (16,32):raise ValueError('Unsupported accumulator lane count')
    slots=int(allocation[2])
    reuse=slots
    if 'DW_SPAN' in code:
        match=re.search(r'static const int DW_SPAN=(\d+);',code)
        valid_span='int span=(!nearest&&depth)?DW_SPAN:32;' in code
        if 'PW_SPAN' in code:
            pw=re.search(r'static const int PW_SPAN=(\d+);',code)
            if not pw or int(pw[1])!=16 or 'int span=nearest?32:(depth?DW_SPAN:PW_SPAN);' not in code or 'block*(PW_SPAN*2)+p*2' not in code:raise ValueError('Unknown paired-pixel recurrence schedule')
            valid_span=True;reuse=min(reuse,int(pw[1]))
        if not match or not valid_span or 'for(int p=0;p<span;p++)' not in code:
            raise ValueError('Unsupported shortened DW recurrence schedule')
        reuse=min(slots,int(match[1]))
        if reuse not in (16,32):raise ValueError('Unverified DW reuse distance')
    blocks=text.split('always @ (*) begin')[1:];ports={}
    for block in blocks:
        # Restrict to the first always block, including its enabling condition.
        block=block.split('always @',1)[0]
        match=re.search(r'(acc(?:_\d+)?)_(ce0|we1)_local = 1\x27b1;',block)
        if not match:continue
        condition=block[:match.start()]
        stages={int(n) for n in re.findall(r'ap_enable_reg_pp0_iter(\d+)',condition)}
        if len(stages)!=1:raise ValueError('Ambiguous recurrence enable '+match[0])
        ports.setdefault(match[1],{})[match[2]]=stages.pop()
    if len(ports)!=lanes:raise ValueError('Expected all allocated accumulator banks')
    result=[]
    for name,stages in sorted(ports.items()):
        if set(stages)!={'ce0','we1'}:raise ValueError('Missing read or write enable '+name)
        delta=stages['we1']-stages['ce0']
        result.append(dict(bank=name,read_stage=stages['ce0'],write_stage=stages['we1'],write_minus_read=delta,safe_before_next_read=0<=delta<reuse))
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(scope='GENERATED_RTL_STATIC_RECURRENCE_CHECK_NOT_SIMULATION_OR_BOARD',hls=str(hls),source_sha256=sha(source),rtl_sha256=sha(rtl),slots=slots,allocated_banks=lanes,minimum_reuse_iterations=reuse,banks=result,all_banks_safe=all(r['safe_before_next_read'] for r in result),interpretation='All stages share the flattened loop enable. A preceding write must occur before the same slot is read again; equality is rejected conservatively. Allocated RAM depth alone is insufficient when DW uses a shorter logical span.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=inspect(a.hls);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
    if not r['all_banks_safe']:raise SystemExit(2)
if __name__=='__main__':main()
