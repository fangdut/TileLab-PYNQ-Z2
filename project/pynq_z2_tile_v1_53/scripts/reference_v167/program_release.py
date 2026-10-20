"""Reprogram a sealed, matching V167 deployment; never write flash."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,ipaddress,zipfile,socket
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'pynq_z2_tile_v1_53.sdk'))
from reserve_boot_id import reserve
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(bundle):
    bundle=Path(bundle).resolve();m=json.loads((bundle/'DEPLOYMENT.json').read_text())
    if (m['release'],m['firmware'],m['pl_id'])!=('V1.67',0x16700,0x16700601):raise ValueError('Wrong release identity')
    for base,records in [(bundle,m['files']),(R,m['source_sha256'])]:
        for name,digest in records.items():
            f=(base/name).resolve()
            if not f.is_relative_to(base) or sha(f)!=digest:raise ValueError('Deployment/source mismatch: '+name)
    s=dict(line.split('=',1) for line in (bundle/'implementation_status.txt').read_text().splitlines() if '=' in line)
    if float(s['setup_slack_ns'])<0 or float(s['hold_slack_ns'])<0 or int(s['drc_errors']):raise ValueError('Timing/DRC failed')
    with zipfile.ZipFile(bundle/'system.xsa') as z:
        bits=[n for n in z.namelist() if n.endswith('.bit')]
        if len(bits)!=1 or hashlib.sha256(z.read(bits[0])).hexdigest()!=sha(bundle/'system.bit'):raise ValueError('XSA/BIT mismatch')
    return m
def run(bundle,xsdb,address,out):
    bundle=Path(bundle).resolve();verify(bundle)
    for port in (8770,8771):
        try:
            connection=socket.create_connection(('127.0.0.1',port),timeout=1)
        except OSError:continue
        connection.close();raise RuntimeError(f'Stop the running station on port{port} before reprogramming')
    address=ipaddress.IPv4Address(address)
    if not address.is_private or address.is_multicast or address.is_unspecified or int(address)&255 in (0,255):raise ValueError('Use private board IPv4')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);boot=reserve(R)
    tcl=(R/'scripts/program_single_tile_verified.tcl').read_text().replace('0x13200','0x16700').replace('0xd06b3b9b','0x16700601')
    init=' source [file join $bundle ps7_init.tcl]\n ps7_init\n ps7_post_config\n';tcl=tcl.replace(init,'').replace(' fpga -file ',init+' fpga -file ',1)
    marker='V167_VOLATILE_STARTUP_PASSED';tcl=tcl.replace('V164 volatile programming and startup register checks passed. This is not accuracy/board acceptance.',marker)
    script=out/'program.tcl';script.write_text(tcl)
    with (out/'program.log').open('w',encoding='utf8') as log:subprocess.run([str(xsdb),str(script),str(bundle),str(boot),str(int(address))],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    transcript=(out/'program.log').read_text(encoding='utf8',errors='replace')
    if transcript.splitlines().count(marker)!=1 or 'PROGRAMMING_FAILED:' in transcript:raise RuntimeError('Board programming/startup failed')
    result=dict(programmed=True,boot_id=boot,address=str(address),deployment_sha256=sha(bundle/'DEPLOYMENT.json'),startup_checks=True,video_verified=False,score_verified=False)
    (out/'proof.json').write_text(json.dumps(result,indent=2)+'\n');return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--xsdb',type=Path,required=True);p.add_argument('--address',default='192.168.33.10');p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.bundle,a.xsdb,a.address,a.out)))
if __name__=='__main__':main()
