"""Candidate-only programming entry. --dry-run verifies files without JTAG.

Requires no running Station. A successful download is not board acceptance.
"""
from pathlib import Path
import argparse,datetime,ipaddress,json,socket,subprocess,sys
from check_support_candidate import verify
R=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--board-ip',required=True);ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--xsdb',type=Path,default=Path('D:/2025.2/Vitis/bin/xsdb.bat'));args=ap.parse_args()
    ip=ipaddress.ip_address(args.board_ip)
    if ip.version!=4 or not ip.is_private or ip.is_unspecified or ip.is_multicast or str(ip).split('.')[-1] in ('0','255'):
        raise ValueError('Use a usable private board IPv4')
    data,digest=verify(R)
    if not data.get('hardware_implemented') or not data.get('software_compiled'):raise RuntimeError('Candidate build is incomplete')
    artifacts=R/'reports/v155/download'
    if args.dry_run:
        print(json.dumps(dict(dry_run=True,no_hardware_access=True,board_ip=str(ip),artifacts=str(artifacts),manifest_sha256=digest)));return
    try:
        with socket.create_connection(('127.0.0.1',8770),timeout=1):pass
    except OSError:pass
    else:raise RuntimeError('A Station owns port 8770; stop it before programming')
    if not args.xsdb.is_file():raise FileNotFoundError(args.xsdb)
    boot=int(subprocess.check_output([sys.executable,str(R/'pynq_z2_tile_v1_53.sdk/reserve_boot_id.py')],text=True).strip())
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=R/'reports/v155/programming'/stamp;out.mkdir(parents=True,exist_ok=False)
    with (out/'xsdb.log').open('x',encoding='utf-8') as log:
        result=subprocess.run([str(args.xsdb),str(R/'scripts/program_support_candidate.tcl'),str(artifacts),str(boot),str(int(ip)),str(out/'jtag_identity.txt'),str(artifacts/'ps7_init.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=180)
    if result.returncode or not (out/'jtag_identity.txt').is_file():raise RuntimeError('Programming failed; see '+str(out/'xsdb.log'))
    verify(R)
    proof=dict(programmed=True,boot_id=boot,firmware_version=0x12d00,board_ip=str(ip),manifest_sha256=digest,
               artifact_sha256={name:value for name,value in data['files'].items() if name.startswith('reports/v155/download/')},
               new_board_acceptance=False)
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    (R/'reports/programmed_v155_candidate.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(dict(programmed=True,boot_id=boot,new_board_acceptance=False)))
if __name__=='__main__':main()

