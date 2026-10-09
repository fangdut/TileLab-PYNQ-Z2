"""Update generated paths after copying; never alter accepted BIT/XSA/ELF."""
from pathlib import Path
import hashlib,json

R=Path(__file__).resolve().parents[1];S=R/(R.name+'.sdk')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert R.name=='pynq_z2_tile_v1_53','Preserve the project folder name'
    artifacts=[S/'system.bit',S/'system.xsa',S/'hdmi_ethernet/build/hdmi_ethernet.elf']
    before={str(p):sha(p) for p in artifacts}
    meta=S/'hdmi_platform/vitis-comp.json'
    old=Path(json.loads(meta.read_text(encoding='utf-8'))['configuration']['xsa']).parents[1]
    pairs=[(str(old).replace('\\','/'),R.as_posix()),(str(old).replace('/','\\'),str(R).replace('/','\\'))]
    pairs+=[(a.replace('\\','\\\\'),b.replace('\\','\\\\')) for a,b in pairs if '\\' in a]
    files=[R/(R.name+'.xpr')]+[p for p in S.rglob('*') if p.is_file() and p.suffix.lower() in ('.json','.xml','.xpfm','.yaml','.yml','.cmake') and '_ide' not in p.parts]
    changed=[]
    for p in files:
        body=p.read_text(encoding='utf-8',errors='strict');new=body
        # Longer escaped spellings first, so replacements cannot partially eat
        # escaped JSON Windows paths. Authoritative application code is excluded.
        for a,b in sorted(pairs,key=lambda v:len(v[0]),reverse=True):new=new.replace(a,b)
        if new!=body:p.write_text(new,encoding='utf-8');changed.append(p.relative_to(R).as_posix())
    assert before=={str(p):sha(p) for p in artifacts}
    print(json.dumps(dict(changed=changed,binaries_unchanged=True)))

if __name__=='__main__':main()
