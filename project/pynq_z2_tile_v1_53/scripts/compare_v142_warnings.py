"""Compare top-level synthesis diagnostics, retaining new warnings for review."""
from pathlib import Path
from collections import Counter
import hashlib,json,re
R=Path(__file__).resolve().parents[1];O=R/'reports/v142'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def warnings(path):
    result=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.startswith(('WARNING:','CRITICAL WARNING:','ERROR:')):continue
        # Only release directory names and source line locations are normalized.
        line=re.sub(r'pynq_z2_tile_v1_\d+','PROJECT',line.replace('\\','/'))
        line=re.sub(r'\.(v|vh|tcl|xdc):\d+(?=\])',r'.\1:LINE',line)
        result.append(line)
    return Counter(result)
def main():
    current=R/(R.name+'.runs')/'synth_1/runme.log'
    base=R.parent/'pynq_z2_tile_v1_41/pynq_z2_tile_v1_41.runs/synth_1/runme.log'
    new,old=warnings(current),warnings(base)
    report=dict(scope='Top-level synthesis diagnostic comparison only; routed timing/clock audits remain mandatory',
        baseline='V1.41',current='V1.42',same_warning_multiset=new==old,
        current_count=sum(new.values()),baseline_count=sum(old.values()),
        new_warnings=list((new-old).elements()),removed_warnings=list((old-new).elements()),
        source_sha256={str(p):sha(p) for p in (current,base)},
        note='OOC clock assumptions are not deployed clock evidence; inspect actual routed clocks.')
    (O/'synthesis_warning_comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    assert report['same_warning_multiset'],'Changed diagnostics require review; do not silently accept'
if __name__=='__main__':main()
