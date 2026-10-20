"""Build an isolated V167 workspace from a matching, timing-approved XSA/BIT."""
from pathlib import Path
import os,shutil,runpy,zipfile,hashlib,json,re
R=Path(__file__).resolve().parents[2]
ws=Path(os.environ['TILE_REF_WORKSPACE']);hw=Path(os.environ['TILE_REF_HARDWARE']);ip=Path(os.environ['TILE_REF_HLS'])/'solution/impl/ip'
if not ws.is_absolute() or ws.suffix!='.sdk' or ws.exists():raise ValueError('Choose a new absolute .sdk workspace')
status=dict(line.split('=',1) for line in (hw/'implementation_status.txt').read_text().splitlines() if '=' in line)
if float(status['setup_slack_ns'])<0 or float(status['hold_slack_ns'])<0 or int(status['drc_errors']):raise ValueError('Timing/DRC failed')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
with zipfile.ZipFile(hw/'system.xsa') as z:
    bits=[n for n in z.namelist() if n.endswith('.bit')]
    if len(bits)!=1 or hashlib.sha256(z.read(bits[0])).hexdigest()!=sha(hw/'system.bit'):raise ValueError('XSA/BIT mismatch')
header=(ip/'drivers/reference_frame_v1_0/src/xreference_frame_hw.h').read_text()
expected={'PAIRED':0x10,'SCORES':0x1c,'GAIN_R':0x28,'GAIN_G':0x30,'GAIN_B':0x38,'OFFSET_R':0x40,'OFFSET_G':0x48,'OFFSET_B':0x50,'HIGH_R':0x58,'LOW_R':0x60}
for name,offset in expected.items():
    match=re.search(r'XREFERENCE_FRAME_CONTROL_ADDR_'+name+r'_DATA\s+(0x[0-9a-fA-F]+)',header)
    if not match or int(match[1],16)!=offset:raise ValueError('Unexpected HLS ABI: '+name)
ws.mkdir();author=R/'pynq_z2_tile_v1_53.sdk'
for name in ('system.xsa','system.bit'):shutil.copy2(hw/name,ws/name)
shutil.copytree(author/'ethernet_sources',ws/'ethernet_sources');shutil.copy2(author/'build_ethernet.py',ws/'build_ethernet.py')
builder=ws/'build_ethernet.py';s=builder.read_text();key="('lwip220_tcp_snd_buf','65535')"
if key not in s:raise ValueError('Cannot identify the authored BSP TCP configuration')
builder.write_text(s.replace(key,key+",('lwip220_tcp_wnd','65535')",1))
src=ws/'ethernet_sources';shutil.copy2(R/'experimental/reference_v167/reference_service.c',src/'reference_service.c')
p=src/'main.c';s=p.read_text().replace('int main(void){','extern void reference_service_start(void),reference_service_poll(void);\nint main(void){').replace('tile_network_start();','tile_network_start();reference_service_start();').replace('tile_network_poll();queue.meta','tile_network_poll();reference_service_poll();queue.meta');p.write_text(s)
p=src/'model_identity_v156.h';p.write_text(p.read_text().replace('0xd06b3b9bu','0x16700601u'))
p=src/'single_tile_profile.h';p.write_text(p.read_text().replace('0x00013200u','0x00016700u').replace('0x32b11135u','0x16700601u'))
p=src/'network.c';s=p.read_text();key=' if(rx[1]==1 &&';assert key in s
s=s.replace(key,''' if(rx[1]==7 && rx[2]==0x16700601u && rx[3]==0){
  want_rle=want_packed=reply_codec=0;queue.meta[M_ENABLE]=1;waiting=1;
  if(queue.head==queue.tail){queue.meta[M_REASON]=2;queue.meta[M_REQUEST]=queue.meta[M_REQUEST_ACK]+1;}
 }else if(rx[1]==1 &&''',1);p.write_text(s)
(ws/'SOURCE_INPUTS.json').write_text(json.dumps({f.name:sha(f) for f in src.iterdir() if f.is_file()},indent=2))
if os.environ.get('TILE_REF_PLATFORM_WORKSPACE'):
    import vitis
    seed=Path(os.environ['TILE_REF_PLATFORM_WORKSPACE'])
    if sha(seed/'system.xsa')!=sha(ws/'system.xsa'):raise ValueError('Reused BSP hardware differs from this exact XSA')
    platform=seed/'hdmi_platform/export/hdmi_platform/hdmi_platform.xpfm'
    if not platform.is_file():raise FileNotFoundError(platform)
    opts=(seed/'hdmi_platform/export/hdmi_platform/sw/standalone_a9/include/lwipopts.h').read_text()
    if not re.search(r'#define\s+TCP_WND\s+65535\b',opts):raise ValueError('Reused BSP must have the full-frame receive window65535')
    client=vitis.create_client()
    try:client.set_workspace(str(ws))
    except Exception as error:
        if 'workspace version' not in str(error):raise
        client.update_workspace(str(ws))
    client.add_platform_repos(str(platform.parent))
    app=client.create_app_component(name='hdmi_ethernet',platform=str(platform),domain='standalone_a9',template='empty_application')
    app.import_files(from_loc=str(ws/'ethernet_sources'),dest_dir_in_cmp='src')
    uc=ws/'hdmi_ethernet/src/UserConfig.cmake';s=uc.read_text();uc.write_text(s.replace('set(USER_COMPILE_OPTIMIZATION_LEVEL -O0)','set(USER_COMPILE_OPTIMIZATION_LEVEL -O2)').replace('set(USER_COMPILE_OTHER_FLAGS )','set(USER_COMPILE_OTHER_FLAGS -fno-builtin-memcpy)'))
    if (ws/'hdmi_ethernet/src/lscript.ld').read_bytes()!=(src/'lscript.ld').read_bytes():raise ValueError('Imported linker script changed')
    app.build();vitis.dispose()
else:runpy.run_path(str(ws/'build_ethernet.py'),run_name='__main__')
(ws/'BUILD_RESULT.json').write_text(json.dumps(dict(elf_sha256=sha(ws/'hdmi_ethernet/build/hdmi_ethernet.elf'),xsa_sha256=sha(ws/'system.xsa'),bit_sha256=sha(ws/'system.bit'),scope='HOST_PREPARED_PAIRS_FULL_FRAME_PL_METRIC'),indent=2))
