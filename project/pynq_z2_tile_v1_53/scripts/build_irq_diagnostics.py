"""Link identical diagnostic sources with the real old/new BSP archives."""
from pathlib import Path
import subprocess,json,hashlib,re,sys
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/irq_context';O.mkdir(parents=True,exist_ok=True)
bin=Path('D:/2025.2/Vitis/gnu/aarch32/nt/gcc-arm-none-eabi/bin')
gcc=bin/'arm-none-eabi-gcc.exe';objdump=bin/'arm-none-eabi-objdump.exe';nm=bin/'arm-none-eabi-nm.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,minor,tag in [('baseline',15,0),('candidate',16,1)]:
 if len(sys.argv)>1 and sys.argv[1]!=name:continue
 root=R.parent/f'pynq_z2_tile_v1_{minor}';ws=root/(root.name+'.sdk')
 bsp=ws/'hdmi_platform/export/hdmi_platform/sw/standalone_a9'
 out=O/name;out.mkdir(exist_ok=True)
 # Equal 1 KiB test stacks isolate context save overhead; production reserves
 # 4 KiB in V1.16. Do not silently use the production stack in just one test.
 oldws=R.parent/'pynq_z2_tile_v1_15/pynq_z2_tile_v1_15.sdk'
 ld=(oldws/'hdmi_ethernet/src/lscript.ld').read_text()
 assert '_IRQ_STACK_SIZE = DEFINED(_IRQ_STACK_SIZE) ? _IRQ_STACK_SIZE : 1024;' in ld
 (out/'diagnostic.ld').write_text(ld)
 flags=['-DSDT','-mcpu=cortex-a9','-mfpu=vfpv3','-mfloat-abi=hard','-O2','-g',
        '-Wall','-Wextra','-specs='+str(bsp/'Xilinx.spec'),'-I'+str(bsp/'include'),f'-DTEST_CANDIDATE={tag}']
 command=[str(gcc),*flags,str(R/'diagnostics/irq_context_test.c'),str(R/'diagnostics/irq_context_probe.S'),
          '-Wl,-T,'+str(out/'diagnostic.ld'),'-Wl,-Map,'+str(out/'diagnostic.map'),'-L'+str(bsp/'lib'),
          '-Wl,--start-group','-lxilstandalone','-lxiltimer','-lxil','-lgcc','-lc','-Wl,--end-group',
          '-o',str(out/'diagnostic.elf')]
 p=subprocess.run(command,capture_output=True,text=True);(out/'compile.log').write_text(p.stdout+p.stderr);p.check_returncode()
 text=subprocess.check_output([str(objdump),'-d',str(out/'diagnostic.elf')],text=True)
 (out/'disassembly.txt').write_text(text)
 symbols=subprocess.check_output([str(nm),'-n',str(out/'diagnostic.elf')],text=True)
 (out/'symbols.txt').write_text(symbols)
 names={m[2]:int(m[0],16) for l in symbols.splitlines() if (m:=l.split()) and len(m)==3}
 needed={k:names[k] for k in ['irq_result','irq_first_expected','irq_first_observed','_irq_stack_end','__irq_stack','IRQHandler','irq_clobber_handler','irq_context_probe']}
 irq=re.search(r'<IRQHandler>:\n(.*?)(?=\n[0-9a-f]+ <)',text,re.S).group(1)
 saves=bool(re.search(r'\bvpush\b',irq));assert saves==bool(tag),(name,irq)
 result=dict(name=name,passed=True,bsp=str(bsp),command=command,elf_sha256=sha(out/'diagnostic.elf'),symbols=needed,
             source_sha256={p.name:sha(p) for p in (R/'diagnostics').iterdir() if p.is_file()},irq_saves_vfp=saves,irq_instructions=irq,
             bsp_archives={p.name:sha(p) for p in (bsp/'lib').glob('*.a')},equal_test_stack_bytes=1024)
 (out/'build.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(dict(variant=name,compiled=True,irq_saves_vfp=saves,elf_sha256=result['elf_sha256'])),flush=True)
