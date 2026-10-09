"""Read only audit of the V1.52 Vitis build and matching XSA/BIT."""
from pathlib import Path
import hashlib,json,re,subprocess,traceback,zipfile
R=Path(__file__).resolve().parents[1];S=R/(R.name+'.sdk');O=R/'reports/v152';TOOLS=Path('D:/2025.2/Vitis/gnu/aarch32/nt/gcc-arm-none-eabi/bin')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 result=dict(passed=False,version='V1.52',scope='Fresh Vitis build paired with fresh V1.52 XSA; static ELF audit only')
 try:
  plan=json.loads((R/'ITERATION_PLAN.json').read_bytes());assert plan['version']=='V1.52'
  elf=S/'hdmi_ethernet/build/hdmi_ethernet.elf';assert elf.exists()
  sources=S/'ethernet_sources';imported=S/'hdmi_ethernet/src'
  source_hash={}
  for p in sources.iterdir():
   if p.is_file() and p.suffix in ('.c','.h'):
    assert (imported/p.name).is_file() and sha(p)==sha(imported/p.name),p.name;source_hash[p.name]=sha(p)
  hdr=(sources/'event_queue.h').read_text();mainc=(sources/'main.c').read_text();net=(sources/'network.c').read_text()
  for x in ('#define M_WIDE_WEAK_REQUEST 88u','#define M_WIDE_WEAK_APPLIED 89u','#define META_WORDS 90u','m[M_VERSION]=0x00012b00u'):assert x in hdr,x
  for x in ('M_WIDE_WEAK_APPLIED','0x08000000u','Tile V1.52 dual-scale weak PL'):assert x in mainc,x
  assert 'rx[3]>>5' in net and 'radius-16' in net
  obj=lambda *a:subprocess.check_output([str(TOOLS/'arm-none-eabi-objdump.exe'),*map(str,a)],text=True,encoding='utf-8',errors='replace')
  dis=obj('-d',elf);(O/'firmware_disassembly.txt').write_text(dis,encoding='utf-8')
  attrs=subprocess.check_output([str(TOOLS/'arm-none-eabi-readelf.exe'),'-A',str(elf)],text=True,encoding='utf-8',errors='replace')
  head=subprocess.check_output([str(TOOLS/'arm-none-eabi-readelf.exe'),'-h',str(elf)],text=True,encoding='utf-8',errors='replace')
  assert 'Machine:                           ARM' in head and 'little endian' in head.lower() and 'Tag_ABI_VFP_args: VFP registers' in attrs
  assert b'Tile V1.52 dual-scale weak PL' in elf.read_bytes()
  user=(S/'hdmi_ethernet/src/UserConfig.cmake').read_text();assert 'set(USER_COMPILE_OPTIMIZATION_LEVEL -O2)' in user and '-fno-builtin-memcpy' in user
  assert b'_IRQ_STACK_SIZE = DEFINED(_IRQ_STACK_SIZE) ? _IRQ_STACK_SIZE : 4096;' in (S/'hdmi_ethernet/src/lscript.ld').read_bytes()
  bit=S/'system.bit';xsa=S/'system.xsa';assert bit.exists() and xsa.exists();assert sha(bit)!=plan['inherited_hardware_sha256']['system.bit'];assert sha(xsa)!=plan['inherited_hardware_sha256']['system.xsa']
  with zipfile.ZipFile(xsa) as z:
   embedded=[hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.lower().endswith('.bit')]
  assert embedded==[sha(bit)]
  result.update(passed=True,firmware_sha256=sha(elf),bit_sha256=sha(bit),xsa_sha256=sha(xsa),sources_sha256=source_hash,wide_weak_protocol=True,abi_hard_float=True,optimization='-O2',irq_stack_bytes=4096,embedded_bit_matches=True)
 except Exception:
  result['error']=traceback.format_exc();raise
 finally:(O/'firmware_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
