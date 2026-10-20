"""Seal matching V167 artifacts and optionally program volatile JTAG RAM."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys,zipfile,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/'pynq_z2_tile_v1_53.sdk'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--hardware',type=Path,required=True);p.add_argument('--software',type=Path,required=True);p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--program',action='store_true');p.add_argument('--xsdb',type=Path);p.add_argument('--address',default='192.168.33.10');a=p.parse_args()
    status=dict(line.split('=',1) for line in (a.hardware/'implementation_status.txt').read_text().splitlines() if '=' in line)
    if float(status['setup_slack_ns'])<0 or float(status['hold_slack_ns'])<0 or int(status['drc_errors']):raise ValueError('Hardware timing/DRC failed')
    build=json.loads((a.software/'BUILD_RESULT.json').read_text());elf=a.software/'hdmi_ethernet/build/hdmi_ethernet.elf'
    for key,path in [('bit_sha256',a.hardware/'system.bit'),('xsa_sha256',a.hardware/'system.xsa'),('elf_sha256',elf)]:
        if sha(path)!=build[key]:raise ValueError('Software/hardware provenance mismatch: '+key)
    with zipfile.ZipFile(a.hardware/'system.xsa') as z:
        bits=[n for n in z.namelist() if n.endswith('.bit')]
        if len(bits)!=1 or hashlib.sha256(z.read(bits[0])).hexdigest()!=sha(a.hardware/'system.bit'):raise ValueError('XSA/BIT mismatch')
    buildroot=a.hardware.parents[2];inputs=json.loads((buildroot/'SOURCE_INPUTS.json').read_text())
    used={k:v for k,v in inputs.items() if k.startswith(('rtl/','ip_repo/','constraints/')) or k in ('scripts/create_project.tcl','scripts/add_capture.tcl','scripts/ps7_preset.tcl','scripts/reference_v167/add_reference.tcl')}
    for name,digest in used.items():
        if sha(buildroot/name)!=digest:raise ValueError('Compiled input changed: '+name)
    cosim=a.hls/'solution/sim/report/reference_frame_cosim.rpt'
    if not any('Verilog' in line and 'Pass' in line for line in cosim.read_text().splitlines()):raise ValueError('Full-frame RTL cosimulation failed')
    hls_binding={}
    for name in ('reference_frame.cpp','test_frame.cpp'):
        if sha(a.hls/'src'/name)!=sha(R/'experimental/reference_v167/hls'/name):raise ValueError('Validated HLS source differs: '+name)
    for f in (a.hls/'solution/impl/ip/hdl').rglob('*'):
        if f.is_file():
            rel=f.relative_to(a.hls/'solution/impl/ip');compiled=buildroot/'ip_repo/reference_frame_v167'/rel
            if sha(f)!=sha(compiled):raise ValueError('Hardware IP differs from cosimulated RTL: '+str(rel))
            hls_binding[rel.as_posix()]=sha(f)
    firmware_inputs=json.loads((a.software/'SOURCE_INPUTS.json').read_text())
    for name,digest in firmware_inputs.items():
        if sha(a.software/'ethernet_sources'/name)!=digest:raise ValueError('Firmware source changed: '+name)
    if sha(R/'experimental/reference_v167/reference_service.c')!=firmware_inputs['reference_service.c']:raise ValueError('Authored reference service differs from compiled firmware')
    lwip=a.software/'hdmi_platform/export/hdmi_platform/sw/standalone_a9/include/lwipopts.h'
    if not lwip.is_file():
        raise ValueError('Final sealing requires the independently built complete BSP workspace')
    if not re.search(r'#define\s+TCP_WND\s+65535\b',lwip.read_text()):raise ValueError('Full-frame TCP receive window has not been configured')
    a.out.mkdir(parents=True,exist_ok=False)
    for name in ('system.bit','system.xsa','implementation_status.txt','timing_summary.rpt','drc.rpt','utilization.rpt','cdc.rpt','bus_skew.rpt','route_status.rpt'):shutil.copy2(a.hardware/name,a.out/name)
    shutil.copy2(elf,a.out/'hdmi_ethernet.elf')
    shutil.copy2(lwip,a.out/'bsp_lwipopts.h')
    (a.out/'HARDWARE_INPUTS.json').write_text(json.dumps(used,indent=2)+'\n')
    (a.out/'FIRMWARE_INPUTS.json').write_text(json.dumps(firmware_inputs,indent=2)+'\n')
    (a.out/'HLS_RTL_BINDING.json').write_text(json.dumps(hls_binding,indent=2)+'\n')
    shutil.copy2(cosim,a.out/'hls_cosim.rpt');shutil.copy2(a.hls/'solution/syn/report/reference_frame_csynth.rpt',a.out/'hls_synthesis.rpt')
    with zipfile.ZipFile(a.hardware/'system.xsa') as z:
        choices=[n for n in z.namelist() if n.endswith('ps7_init.tcl')]
        if len(choices)!=1:raise ValueError('Expected exactly one PS initialization script')
        (a.out/'ps7_init.tcl').write_bytes(z.read(choices[0]))
    source_names=['host/reference_frame_tcp.py','host/reference_capture.py','host/reference_station.py','host/reference_station.html','tools/reference_tile/frame_v167.py','tools/reference_tile/registration_v167.py','tools/reference_tile/photometric_v167.py','tools/reference_tile/reference_v166.py','tools/reference_tile/reference_tile.py','config/reference_v165.json','host/workstation.py','host/event_identity.py','scripts/program_single_tile_verified.tcl','pynq_z2_tile_v1_53.sdk/reserve_boot_id.py']
    source_names+=['scripts/reference_v167/'+name for name in ('build_hls.tcl','build_software.py','prepare_video_build.py','add_reference.tcl','program_release.py','seal_and_program.py')]
    source_names+=['pynq_z2_tile_v1_53.sdk/build_ethernet.py']+[f.relative_to(R).as_posix() for f in (R/'pynq_z2_tile_v1_53.sdk/ethernet_sources').iterdir() if f.is_file()]
    sources=[f for f in (R/'experimental/reference_v167').rglob('*') if f.is_file()]+[R/name for name in source_names]
    manifest=dict(release='V1.67',scope='HDMI_CAPTURE_PLUS_HOST_PREPARED_FULL_FRAME_PL_REFERENCE_METRIC',firmware=0x16700,pl_id=0x16700601,accuracy_qualified=False,autonomous_arm_registration=False,source_sha256={f.relative_to(R).as_posix():sha(f) for f in sources},files={f.name:sha(f) for f in a.out.iterdir() if f.is_file()},build=build)
    (a.out/'DEPLOYMENT.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if not a.program:print(json.dumps(dict(sealed=True,path=str(a.out))));return
    if not a.xsdb:raise ValueError('--xsdb required to program')
    from program_release import run
    print(json.dumps(run(a.out,a.xsdb,a.address,a.out/'programming')))
if __name__=='__main__':main()
