from pathlib import Path
import hashlib,json
import vitis
ws=Path(__file__).resolve().parent
# A lightweight version backup carries the old ELF, but not Vitis component
# metadata. Preserve that precisely identified placeholder before asking Vitis
# to create a real component; never delete or relocate an unknown source tree.
app_seed=ws/'hdmi_ethernet'
if app_seed.exists() and not (app_seed/'vitis-comp.json').exists():
    if app_seed.is_symlink() or app_seed.is_junction():
        raise RuntimeError('Refusing linked application placeholder')
    entries=list(app_seed.rglob('*'))
    if any(p.is_symlink() or p.is_junction() for p in entries):
        raise RuntimeError('Refusing linked content in application placeholder')
    if {p.relative_to(app_seed).as_posix() for p in entries}!={'build','build/hdmi_ethernet.elf'}:
        raise RuntimeError('Existing application directory is not the known ELF-only placeholder')
    old_elf=app_seed/'build/hdmi_ethernet.elf'
    plan=json.loads((ws.parent/'ITERATION_PLAN.json').read_text(encoding='utf-8-sig'))
    digest=hashlib.sha256(old_elf.read_bytes()).hexdigest()
    if digest!=plan['inherited_hardware_sha256']['hdmi_ethernet/build/hdmi_ethernet.elf']:
        raise RuntimeError('Application placeholder does not match the inherited ELF')
    preserved=ws/'_inherited_hdmi_ethernet'
    if preserved.exists() or not app_seed.resolve().is_relative_to(ws.resolve()) or not preserved.resolve().is_relative_to(ws.resolve()):
        raise RuntimeError('Unsafe or occupied placeholder preservation path')
    app_seed.rename(preserved)
    print('Preserved inherited ELF-only directory:',preserved,flush=True)
client=vitis.create_client()
try:client.set_workspace(str(ws))
except Exception as e:
    if 'workspace version' not in str(e):raise
    client.update_workspace(str(ws))
platform=client.get_component(name='hdmi_platform') if (ws/'hdmi_platform/vitis-comp.json').exists() else client.create_platform_component(name='hdmi_platform',hw_design=str(ws/'system.xsa'),os='standalone',cpu='ps7_cortexa9_0',domain_name='standalone_a9')
platform.update_hw(hw_design=str(ws/'system.xsa'))
domain=platform.get_domain(name='standalone_a9')
# The application and BSP use hard-float ABI. The Cortex-A9 exception vectors
# must preserve caller-clobbered FP registers even for integer-only callers.
# Keep all vendor defaults and configure through the supported domain API.
flags=domain.get_config(option='proc',param='proc_extra_compiler_flags')['value']
if '-DFPU_HARD_FLOAT_ABI_ENABLED=1' not in flags.split():
    domain.set_config(option='proc',param='proc_extra_compiler_flags',
                      value=flags+' -DFPU_HARD_FLOAT_ABI_ENABLED=1')
if not (ws/'hdmi_platform/ps7_cortexa9_0/standalone_a9/bsp/include/lwipopts.h').exists():
    domain.set_lib(lib_name='lwip220')
for param,value in [('lwip220_api_mode','RAW_API'),('lwip220_dhcp','true'),('lwip220_lwip_dhcp_does_acd_check','false'),('lwip220_ipv6_enable','false'),('lwip220_tcp_snd_buf','65535'),('lwip220_mem_size','524288'),('lwip220_memp_n_tcp_seg','1024'),('lwip220_memp_n_pbuf','512'),('lwip220_n_tx_descriptors','256'),('lwip220_n_rx_descriptors','128')]:
    domain.set_config(option='lib',param=param,value=value,lib_name='lwip220')
platform.build()
app=client.get_component(name='hdmi_ethernet') if (ws/'hdmi_ethernet/vitis-comp.json').exists() else client.create_app_component(name='hdmi_ethernet',platform=str(ws/'hdmi_platform/export/hdmi_platform/hdmi_platform.xpfm'),domain='standalone_a9',template='empty_application')
app.import_files(from_loc=str(ws/'ethernet_sources'),dest_dir_in_cmp='src')
# Reserve additional IRQ stack for the 200-byte FP save area and C handlers.
# The authored linker script is the source of truth for full and app-only builds.
ld=ws/'hdmi_ethernet/src/lscript.ld';s=ld.read_text()
if '_IRQ_STACK_SIZE = DEFINED(_IRQ_STACK_SIZE) ? _IRQ_STACK_SIZE : 4096;' not in s:
    raise RuntimeError('Unexpected IRQ stack linker declaration')
if s!=(ws/'ethernet_sources/lscript.ld').read_text():
    raise RuntimeError('Imported linker script differs from authored source')
uc=ws/'hdmi_ethernet/src/UserConfig.cmake';s=uc.read_text();uc.write_text(s.replace('set(USER_COMPILE_OPTIMIZATION_LEVEL -O0)','set(USER_COMPILE_OPTIMIZATION_LEVEL -O2)').replace('set(USER_COMPILE_OTHER_FLAGS )','set(USER_COMPILE_OTHER_FLAGS -fno-builtin-memcpy)'))
app.build()
if not (ws/'hdmi_ethernet/build/hdmi_ethernet.elf').exists():raise RuntimeError('Network ELF missing')
vitis.dispose()
