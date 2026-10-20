"""Verify and program the isolated HPD experiment; not a reference detector.

The old XSA is used ONLY as the unchanged AXI address map, never presented as
containing the ECO bitstream. No flash is written. The V164 bundle stays sealed.
"""
from pathlib import Path
import argparse,datetime,json,subprocess,sys,ipaddress
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from deployment_single_tile import verify,sha
from program_single_tile import verify_programming_log,ensure_workstation_stopped

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--build',type=Path,required=True);ap.add_argument('--base-dcp',type=Path);ap.add_argument('--xsdb',type=Path,required=True);ap.add_argument('--address',default='192.168.33.10');ap.add_argument('--out',required=True,type=Path);ap.add_argument('--keep-ps-clocks',action='store_true');a=ap.parse_args()
    bundle=ROOT/'releases/v164';m=verify(bundle);build=a.build.resolve();bit=build/'headless_transport.bit'
    if a.base_dcp:
        dcp=a.base_dcp.resolve()
        if sha(dcp.with_name('system.bit'))!=m['files']['system.bit']:raise ValueError('Base checkpoint does not accompany the frozen BIT')
        dcp_digest=sha(dcp)
    else:
        seal=json.loads((build/'HEADLESS_MANIFEST.json').read_text())
        if seal['scope']!='V164_HEADLESS_TRANSPORT_NOT_REFERENCE_ALGORITHM' or seal['base_deployment_sha256']!=sha(bundle/'DEPLOYMENT.json') or seal['eco_script_sha256']!=sha(Path(__file__).with_name('headless_hpd_eco.tcl')):raise ValueError('Headless release provenance mismatch')
        for name,digest in seal['files'].items():
            path=(build/name).resolve()
            if not path.is_relative_to(build) or sha(path)!=digest:raise ValueError('Headless release artifact mismatch')
        dcp_digest=seal['base_dcp_sha256']
    status=dict(line.split('=',1) for line in (build/'implementation_status.txt').read_text().splitlines() if '=' in line)
    if float(status['setup_slack_ns'])<0 or float(status['hold_slack_ns'])<0 or int(status['drc_errors']):raise ValueError('ECO timing/DRC failed')
    address=ipaddress.IPv4Address(a.address)
    if not address.is_private or address.is_unspecified or address.is_multicast or int(address)&255 in (0,255):raise ValueError('Use a private lab IPv4 address')
    ensure_workstation_stopped()
    a.out.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(ROOT/'pynq_z2_tile_v1_53.sdk'));from reserve_boot_id import reserve
    boot=reserve(ROOT)
    tcl=(ROOT/'scripts/program_single_tile_verified.tcl').read_text()
    tcl=tcl.replace('fpga -file [file join $bundle system.bit]','fpga -file {'+bit.as_posix()+'}')
    # Initialize the PS reference clock before asserting the independent HPD.
    # Otherwise the PC can query EDID while its emulation clock is still off.
    initialization=' source [file join $bundle ps7_init.tcl]\n ps7_init\n ps7_post_config\n'
    tcl=tcl.replace(initialization,'')
    tcl=tcl.replace(' fpga -file ',initialization+' fpga -file ',1)
    if a.keep_ps_clocks:
        # Require a known initialized PS before preserving its clock/DDR setup.
        sys.path.insert(0,str(ROOT/'host'));from single_tile_station import SingleTileBridge
        bridge=SingleTileBridge(str(address))
        try:peer=bridge.stats()
        finally:bridge.close()
        if not peer['single_tile']['verified']:raise ValueError('Warm reprogram requires verified running PS')
        tcl=tcl.replace(' rst -system\n after 1000\n','')
        tcl=tcl.replace(' source [file join $bundle ps7_init.tcl]\n ps7_init\n ps7_post_config\n','')
    script=a.out/'program.tcl';script.write_text(tcl)
    before=dict(bit_sha256=sha(bit),base_dcp_sha256=dcp_digest,base_deployment_sha256=sha(bundle/'DEPLOYMENT.json'),eco_script_sha256=sha(Path(__file__).with_name('headless_hpd_eco.tcl')),program_script_sha256=sha(script))
    (a.out/'preflight.json').write_text(json.dumps(before,indent=2)+'\n')
    with (a.out/'program.log').open('w',encoding='utf8') as log:subprocess.run([str(a.xsdb),str(script),str(bundle),str(boot),str(int(address))],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    verify_programming_log(a.out/'program.log')
    if sha(bit)!=before['bit_sha256']:raise ValueError('Bitstream changed during programming')
    result=dict(scope='V164_FROZEN_DETECTOR_WITH_HEADLESS_HPD_ECO_NOT_V166_REFERENCE_MODE',programmed=True,startup_checks_passed=True,accuracy_qualified=False,video_accepted=False,reference_mode_integrated=False,ps_clocks_preserved=a.keep_ps_clocks,boot_id=boot,address=str(address),implementation_status=status,**before)
    (a.out/'proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
