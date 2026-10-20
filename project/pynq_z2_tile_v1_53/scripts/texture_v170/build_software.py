"""Fresh ARM transport BSP, with source/model/ABI and timing checks."""
from pathlib import Path
import os,hashlib,json,shutil,re,zipfile
import vitis
from verify_reset import verify
root=Path(__file__).resolve().parents[2]
ws=Path(os.environ['TILE_TEXTURE_SW']);hw=Path(os.environ['TILE_TEXTURE_HW'])
hls=Path(os.environ['TILE_TEXTURE_HLS']);model=Path(os.environ['TILE_TEXTURE_MODEL'])
if not ws.is_absolute() or ws.exists():raise ValueError('Use new absolute software workspace')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
status=json.loads((hw/'implementation_status.json').read_text())
reset_proof=verify(hw)
if status['setup_slack_ns']<0 or status['hold_slack_ns']<0 or status['drc_errors']:raise ValueError('Unaccepted implementation')
with zipfile.ZipFile(hw/'system.xsa') as z:
    bits=[n for n in z.namelist() if n.endswith('.bit')]
    if len(bits)!=1 or hashlib.sha256(z.read(bits[0])).hexdigest()!=sha(hw/'system.bit'):raise ValueError('XSA bitstream mismatch')
header=(hls/'solution/impl/ip/drivers/texture_integer_v1_0/src/xtexture_integer_hw.h').read_text()
for name,offset in dict(MODEL=0x10,WORK=0x1c,RGB=0x28,RESULT=0x34,WIDTH=0x40,HEIGHT=0x48).items():
    m=re.search(r'XTEXTURE_INTEGER_CONTROL_ADDR_'+name+r'_DATA\s+(0x[0-9a-fA-F]+)',header)
    if not m or int(m[1],16)!=offset:raise ValueError('HLS ABI mismatch: '+name)
graph=json.loads((model/'graph.json').read_text())
if sha(model/'model.bin')!=graph['sha256']:raise ValueError('Model SHA mismatch')
ws.mkdir();src=ws/'sources';src.mkdir()
shutil.copy2(root/'experimental/texture_v170/firmware/main.c',src/'main.c')
seed=root/'pynq_z2_tile_v1_53.sdk/ethernet_sources'
shutil.copy2(seed/'safe_memcpy.c',src/'safe_memcpy.c')
ld=(seed/'lscript.ld').read_text().replace('LENGTH = 0x0ff00000','LENGTH = 0x05e00000').replace('/* Tile V1.3 reserves DDR >= 0x10000000 for PL capture. */','/* V170 reserves DDR >= 0x05f00000 for PL inference and status. */')
(src/'lscript.ld').write_text(ld)
(src/'model_identity.h').write_text(f'#define MODEL_BYTES {graph["model_bytes"]}u\n#define MODEL_CRC {graph["crc32"]}u\n#define MODEL_GRID {graph["grid"]}u\n')
shutil.copy2(hw/'system.xsa',ws/'system.xsa')
client=vitis.create_client()
try:
    try:client.set_workspace(str(ws))
    except Exception as error:
        if 'workspace version' not in str(error):raise
        client.update_workspace(str(ws))
    platform=client.create_platform_component(name='texture_platform',hw_design=str(ws/'system.xsa'),os='standalone',cpu='ps7_cortexa9_0',domain_name='standalone_a9')
    domain=platform.get_domain(name='standalone_a9')
    flags=domain.get_config(option='proc',param='proc_extra_compiler_flags')['value']
    domain.set_config(option='proc',param='proc_extra_compiler_flags',value=flags+' -DFPU_HARD_FLOAT_ABI_ENABLED=1')
    domain.set_lib(lib_name='lwip220')
    for p,v in [('lwip220_api_mode','RAW_API'),('lwip220_dhcp','false'),('lwip220_ipv6_enable','false'),('lwip220_tcp_snd_buf','65535'),('lwip220_tcp_wnd','65535'),('lwip220_mem_size','524288'),('lwip220_memp_n_tcp_seg','1024'),('lwip220_memp_n_pbuf','512'),('lwip220_n_tx_descriptors','256'),('lwip220_n_rx_descriptors','128')]:
        domain.set_config(option='lib',param=p,value=v,lib_name='lwip220')
    platform.build()
    app=client.create_app_component(name='texture_transport',platform=str(ws/'texture_platform/export/texture_platform/texture_platform.xpfm'),domain='standalone_a9',template='empty_application')
    app.import_files(from_loc=str(src),dest_dir_in_cmp='src')
    uc=ws/'texture_transport/src/UserConfig.cmake';s=uc.read_text();uc.write_text(s.replace('set(USER_COMPILE_OPTIMIZATION_LEVEL -O0)','set(USER_COMPILE_OPTIMIZATION_LEVEL -O2)').replace('set(USER_COMPILE_OTHER_FLAGS )','set(USER_COMPILE_OTHER_FLAGS -fno-builtin-memcpy)'))
    app.build()
finally:vitis.dispose()
elf=ws/'texture_transport/build/texture_transport.elf'
if not elf.is_file():raise RuntimeError('ELF not built')
(ws/'BUILD_RESULT.json').write_text(json.dumps(dict(elf_sha256=sha(elf),xsa_sha256=sha(hw/'system.xsa'),bit_sha256=sha(hw/'system.bit'),model_sha256=graph['sha256'],reset_proof=reset_proof,sources={p.name:sha(p) for p in src.iterdir()},scope='ARM_TRANSPORT_ONLY_FULL_PL_INFERENCE'),indent=2))
