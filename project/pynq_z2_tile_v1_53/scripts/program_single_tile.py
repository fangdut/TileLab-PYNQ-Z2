"""Verify V164 bundle; --program explicitly performs volatile JTAG programming."""
from pathlib import Path
import argparse,datetime,ipaddress,json,subprocess,sys,urllib.error,urllib.request
from deployment_single_tile import ROOT,verify

SUCCESS='V164 volatile programming and startup register checks passed. This is not accuracy/board acceptance.'

def verify_programming_log(path):
    text=Path(path).read_text(encoding='utf8',errors='replace')
    # xsdb.bat may return0 even when Tcl exits1: the tool transcript is required.
    if text.splitlines().count(SUCCESS)!=1 or 'PROGRAMMING_FAILED:' in text:
        raise RuntimeError('XSDB did not confirm all startup checks; inspect '+str(path))

def ensure_workstation_stopped():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8770/api/live',timeout=2):raise RuntimeError('Stop the running workstation and settle pending events before reprogramming')
    except urllib.error.URLError:pass

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--bundle',type=Path,default=ROOT/'releases/v164');ap.add_argument('--program',action='store_true');ap.add_argument('--xsdb',type=Path);ap.add_argument('--address',default='169.254.200.10');a=ap.parse_args();bundle=a.bundle.resolve();manifest=verify(bundle)
    if not a.program:print(json.dumps(dict(verified=True,release=manifest['release'],programmed=False)));return
    if a.xsdb is None or not a.xsdb.is_file():raise ValueError('Pass --xsdb with the installed Vitis XSDB executable')
    ipvalue=0
    if a.address!='dhcp':
        ip=ipaddress.IPv4Address(a.address);nets=map(ipaddress.IPv4Network,['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','169.254.1.0/24','169.254.0.0/16'])
        if not any(ip in n for n in nets) or int(ip)&255 in (0,255):raise ValueError('Use a usable private/direct-link IPv4 address')
        ipvalue=int(ip)
    ensure_workstation_stopped()
    sys.path.insert(0,str(ROOT/'pynq_z2_tile_v1_53.sdk'));from reserve_boot_id import reserve
    boot=reserve(ROOT);out=ROOT/'reports/v164/programming';out.mkdir(parents=True,exist_ok=True);name=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+str(boot)
    with (out/(name+'.log')).open('w',encoding='utf8') as log:
        subprocess.run([str(a.xsdb),str(ROOT/'scripts/program_single_tile_verified.tcl'),str(bundle),str(boot),str(ipvalue)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    verify_programming_log(out/(name+'.log'))
    proof=dict(programmed=True,board_acceptance=False,accuracy_qualified=False,boot_id=boot,address=a.address,profile_sha256=manifest['profile_sha256'],files=manifest['files'])
    (out/(name+'.json')).write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))

if __name__=='__main__':main()
