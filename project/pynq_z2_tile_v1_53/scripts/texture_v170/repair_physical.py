"""Guarded postroute-only repair. Preserve failure; export only accepted timing."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,zipfile
from verify_video import verify,verify_bus_skew_report


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def bit_parts(raw):
    pos=2+int.from_bytes(raw[:2],'big')
    if int.from_bytes(raw[pos:pos+2],'big')!=1:raise ValueError('Unknown BIT header')
    pos+=2;fields={}
    while pos<len(raw):
        tag=chr(raw[pos]);pos+=1;size_bytes=4 if tag=='e' else 2
        n=int.from_bytes(raw[pos:pos+size_bytes],'big');pos+=size_bytes
        value=raw[pos:pos+n];pos+=n
        if len(value)!=n:raise ValueError('Truncated BIT')
        if tag=='e':
            if pos!=len(raw) or set(fields)!=set('abcd'):raise ValueError('Unexpected BIT layout')
            return fields,value
        fields[tag]=value
    raise ValueError('BIT configuration payload missing')


def main():
    p=argparse.ArgumentParser();p.add_argument('--hardware',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seal-existing',action='store_true');a=p.parse_args()
    if not a.seal_existing and ((a.hardware/'system.xsa').exists() or (a.hardware/'system.bit').exists()):
        raise ValueError('Do not replace an already exported build with this repair helper')
    if not verify(a.hardware)['video']:raise ValueError('Expected video candidate')
    original=a.out/'original_failure';snapshot=a.out/'repair_postroute.tcl'
    if not a.seal_existing:
        a.out.mkdir(parents=True,exist_ok=False);original.mkdir()
        for name in ['implementation_status.json','timing_summary.rpt','utilization.rpt','drc.rpt','candidate_preflight.json']:
            shutil.copy2(a.hardware/name,original/name)
    initial=json.loads((original/'implementation_status.json').read_text())
    if initial['setup_slack_ns']>=0 and initial['hold_slack_ns']>=0:
        raise ValueError('No timing failure to repair')
    if not a.seal_existing:
        script=Path(__file__).with_name('repair_postroute.tcl');shutil.copy2(script,snapshot)
        env=os.environ.copy();env.update(TILE_TEXTURE_HW=str(a.hardware),TILE_TEXTURE_REPAIR=str(a.out))
        with (a.out/'console.log').open('w') as log:
            run=subprocess.run(['D:/2025.2/Vivado/bin/vivado.bat','-mode','batch','-source',str(snapshot),
                '-notrace','-nolog','-nojournal'],cwd=a.hardware,env=env,stdout=log,stderr=subprocess.STDOUT)
        if run.returncode:raise RuntimeError('Physical repair failed; no programming')
    if 'TEXTURE_VIDEO_POSTROUTE_REPAIR_PASSED' not in (a.out/'console.log').read_text():
        raise RuntimeError('Physical repair not accepted; no programming')
    status=json.loads((a.hardware/'implementation_status.json').read_text())
    if status['setup_slack_ns']<0 or status['hold_slack_ns']<0 or status['drc_errors'] or status['dsp']>220:
        raise RuntimeError('Physical repair guard failed')
    skew=verify_bus_skew_report(a.hardware/'bus_skew.rpt')
    with zipfile.ZipFile(a.hardware/'system.xsa') as z:
        names=[n for n in z.namelist() if n.endswith('.bit')]
        if len(names)!=1:raise ValueError('Ambiguous XSA bitstream')
        embedded=z.read(names[0]);external=(a.hardware/'system.bit').read_bytes()
        if embedded!=external:
            eh,ep=bit_parts(embedded);lh,lp=bit_parts(external)
            if ep!=lp or any(eh[k]!=lh[k] for k in 'ab'):
                raise ValueError('Export configuration payload/design/part differs; canonicalization blocked')
            shutil.copy2(a.hardware/'system.bit',a.out/'before_canonical_external.bit')
            alignment=dict(scope='DATE_TIME_HEADER_ONLY_CANONICALIZATION_FULL_FILE_CHECK_RETAINED',
                payload_sha256=hashlib.sha256(ep).hexdigest(),payload_bytes=len(ep),
                old_external_sha256=hashlib.sha256(external).hexdigest(),
                canonical_sha256=hashlib.sha256(embedded).hexdigest(),
                external_header={k:v.rstrip(b'\0').decode() for k,v in lh.items()},
                embedded_header={k:v.rstrip(b'\0').decode() for k,v in eh.items()})
            (a.out/'canonical_header_alignment.json').write_text(json.dumps(alignment,indent=2)+'\n')
            (a.hardware/'system.bit').write_bytes(embedded)
        if hashlib.sha256(embedded).hexdigest()!=sha(a.hardware/'system.bit'):
            raise ValueError('Canonical full BIT/XSA SHA mismatch')
    proof=dict(scope='TIMING_CLOSED_POSTROUTE_PHYSICAL_REPAIR_NOT_PROGRAMMED',
        bit_sha256=sha(a.hardware/'system.bit'),xsa_sha256=sha(a.hardware/'system.xsa'),
        original_failed_status_sha256=sha(original/'implementation_status.json'),
        repair_script_sha256=sha(snapshot),kernel_sha256=sha(a.hardware/'texture_integer_source.cpp'),
        status=status,gray_skew=skew,clock_changed=False,algorithm_changed=False,
        reports={name:sha(a.hardware/name) for name in ['timing_summary.rpt','bus_skew.rpt','video_cdc.rpt','utilization.rpt','drc.rpt']})
    (a.hardware/'physical_repair.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof),flush=True)


if __name__=='__main__':main()
