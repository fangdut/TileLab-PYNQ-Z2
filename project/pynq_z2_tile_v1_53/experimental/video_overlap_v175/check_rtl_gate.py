"""Bind every overlap HDL file to current passing unit/integration evidence."""
from pathlib import Path
import argparse,json,hashlib
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inspect(path,base):
    gate=json.loads(path.read_text())
    if gate['scope']!='SOURCE_BOUND_OVERLAP_RTL_GATE_NOT_BOARD' or not gate['passed']:
        raise ValueError('Wrong overlap RTL gate')
    actual={p.name:sha(p) for p in (base/'rtl').iterdir() if p.suffix in ('.v','.sv')}
    if actual!=gate['rtl_sources']:raise ValueError('Overlap HDL changed after passing regression')
    if set(gate['tests'])!={'queue','scheduler','writer','pipeline','video_regs','hpd','result_latch'}:
        raise ValueError('All seven overlap RTL regressions required')
    for role,record in gate['tests'].items():
        summary=Path(record['summary'])
        if sha(summary)!=record['sha256']:raise ValueError('RTL regression summary changed: '+role)
        j=json.loads(summary.read_text())
        if not j['passed']:raise ValueError('RTL regression failed: '+role)
        for name,digest in j['sources'].items():
            if sha(base/Path(name))!=digest:raise ValueError('Tested source differs: '+name)
    return gate
def main():
    p=argparse.ArgumentParser()
    roles=['queue','scheduler','writer','pipeline','video_regs','hpd','result_latch']
    for role in roles:p.add_argument('--'+role,type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();base=Path(__file__).resolve().parent
    if a.out.exists():raise ValueError('Fresh gate output required')
    tests={role:dict(summary=str(getattr(a,role)/'summary.json'),sha256=sha(getattr(a,role)/'summary.json')) for role in roles}
    gate=dict(scope='SOURCE_BOUND_OVERLAP_RTL_GATE_NOT_BOARD',passed=True,tests=tests,
        rtl_sources={f.name:sha(f) for f in (base/'rtl').iterdir() if f.suffix in ('.sv','.v')})
    # The alarm border is the only unchanged HDL file not exercised by these
    # fixtures. Bind it to the accepted original implementation separately.
    if (base/'rtl/video_alarm_border.v').read_bytes()!=(base.parent/'video_v171/rtl/video_alarm_border.v').read_bytes():
        raise ValueError('Alarm border changed without its own regression')
    a.out.write_text(json.dumps(gate,indent=2)+'\n');inspect(a.out,base)
    print(json.dumps(dict(passed=True,rtl_files=len(gate['rtl_sources']),tests=list(tests))),flush=True)
if __name__=='__main__':main()
