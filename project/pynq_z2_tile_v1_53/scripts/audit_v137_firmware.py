"""Read-only ELF/build audit after the fresh V1.37 Vitis build.

This script does not build, program, connect to a board, or import old scripts.
It writes only its current-release report. Native tests remain native evidence;
ELF inspection is not a claim that physical interrupt paths were all exercised.
"""
from datetime import datetime, timezone
from pathlib import Path
import difflib
import hashlib
import json
import re
import subprocess
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SDK=ROOT/(ROOT.name+'.sdk')
OUT=ROOT/'reports/v137'
TOOLS=Path('D:/2025.2/Vitis/gnu/aarch32/nt/gcc-arm-none-eabi/bin')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def tool(name,*args):
    return subprocess.check_output([str(TOOLS/('arm-none-eabi-'+name+'.exe')),*map(str,args)],
                                   text=True,encoding='utf-8',errors='strict')


def functions(disassembly):
    result={};name=None
    for line in disassembly.splitlines():
        match=re.match(r'^[0-9a-f]+ <([^>]+)>:',line)
        if match:name=match[1];result[name]=[]
        elif name:result[name].append(line)
    return {name:'\n'.join(lines) for name,lines in result.items()}


def materialized_constants(body):
    """Record ARM immediate construction, clearing registers at other writes.

    This establishes linked immediate values, not a complete CPU emulator or
    execution/reachability proof. Compile/source/native checks provide context.
    """
    registers={};found=[]
    for line in body.splitlines():
        match=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f]+\s+(\w+)\s+(.*)',line)
        if not match:continue
        address,operation,args=match.groups()
        immediate=re.match(r'(\w+),\s*#(0x[0-9a-f]+|\d+)\b',args)
        if operation in ('mov','movw','movt') and immediate:
            register,number=immediate.groups();value=int(number,0)
            if operation=='movt':
                if register not in registers:continue
                value=(registers[register]&65535)|(value<<16)
            registers[register]=value
            found.append(dict(address=address,register=register,value=value,instruction=line.strip()))
        elif operation in ('bl','blx'):
            for register in ('r0','r1','r2','r3','ip','lr'):registers.pop(register,None)
        elif not operation.startswith(('b','str','stm','cmp','cmn','tst','teq','push')):
            registers.pop(args.split(',')[0].strip(),None)
    return found


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    result=dict(passed=False,revision='V1.37',started_utc=datetime.now(timezone.utc).isoformat(),
                scope='Fresh current-root source/import and linked ARM ELF audit; no build or board operation.',
                limitations=['Linked constants and static IRQ instructions are not a full execution/reachability proof.',
                             'Native C results use mocked MMIO/lwIP; physical-board evidence is reported separately.'])
    try:
        plan=read(ROOT/'ITERATION_PLAN.json');assert plan['version']=='V1.37'
        baseline=Path(plan['baseline']);old_sdk=baseline/(baseline.name+'.sdk')
        assert sha(baseline/'DELIVERY_MANIFEST.json')==plan['baseline_manifest_sha256']
        assert sha(Path(plan['backup']))==plan['backup_sha256']
        authored=SDK/'ethernet_sources';imported=SDK/'hdmi_ethernet/src'
        source_hashes={};changes=[];diff=[]
        for path in sorted(authored.iterdir()):
            if not path.is_file():continue
            assert (imported/path.name).is_file(),'Missing imported source: '+path.name
            digest=sha(path);assert digest==sha(imported/path.name),'Authored/import mismatch: '+path.name
            source_hashes[path.name]=digest
            old=(old_sdk/'ethernet_sources'/path.name).read_text(encoding='utf-8')
            new=path.read_text(encoding='utf-8')
            if old!=new:
                changes.append(path.name)
                diff.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
                            fromfile='V1.36/'+path.name,tofile='V1.37/'+path.name))
        assert set(changes)=={'event_queue.h','main.c','network.c'},changes
        (OUT/'firmware_changes.diff').write_text(''.join(diff),encoding='utf-8')
        native=read(OUT/'firmware_native_summary.json');assert native['passed'] is True
        for name,digest in native['source_sha256'].items():assert source_hashes[name]==digest,name
        for name,digest in native['proof_sha256'].items():assert sha(OUT/name)==digest,name
        gate=read(OUT/'product_gate_native/summary.json');assert gate['passed'] is True
        header=(authored/'event_queue.h').read_text()
        for expression in (r'M_PRODUCT_GATE_REQUEST\s+86u',r'M_PRODUCT_GATE_APPLIED\s+87u',
                           r'META_WORDS\s+88u',r'M_VERSION\]=0x00012500u'):
            assert re.search(expression,header),expression
        assert '0x54465337u' in (authored/'main.c').read_text()
        assert "32'h54465337" in (ROOT/'rtl/frame_capture_sg.v').read_text()

        hardware={name:sha(SDK/name) for name in ('system.bit','system.xsa','system.ltx')}
        for name in ('system.bit','system.xsa'):
            assert hardware[name]!=plan['inherited_hardware_sha256'][name],'Inherited artifact: '+name
        with zipfile.ZipFile(SDK/'system.xsa') as archive:
            embedded={name:hashlib.sha256(archive.read(name)).hexdigest()
                      for name in archive.namelist() if name.lower().endswith('.bit')}
        assert len(embedded)==1 and list(embedded.values())==[hardware['system.bit']],embedded

        elf=SDK/'hdmi_ethernet/build/hdmi_ethernet.elf';elf_sha=sha(elf)
        assert elf_sha!=plan['inherited_hardware_sha256']['hdmi_ethernet/build/hdmi_ethernet.elf']
        assert b'Tile V1.37 PL products/best-frame;' in elf.read_bytes(),'Linked version string missing'
        disassembly=tool('objdump','-d',elf);bodies=functions(disassembly)
        (OUT/'firmware_disassembly.txt').write_text(disassembly,encoding='utf-8')
        required=('IRQHandler','memcpy','main','config','tile_capture_health')
        assert all(name in bodies for name in required),list(bodies)
        irq=bodies['IRQHandler']
        irq_patterns=(r'vpush\s+\{d0-d7\}',r'vpush\s+\{d16-d31\}',r'vmrs\s+r1, fpscr',
                      r'vmrs\s+r1, fpexc',r'vmsr\s+fpexc, r1',r'vmsr\s+fpscr, r1',
                      r'vpop\s+\{d16-d31\}',r'vpop\s+\{d0-d7\}')
        for expression in irq_patterns:assert re.search(expression,irq),expression
        assert not re.search(r'\t(v[a-z][a-z0-9.]*)\s',bodies['memcpy']),'Integer memcpy replaced'
        symbols={parts[2]:int(parts[0],16) for line in tool('nm','-n',elf).splitlines()
                 if len(parts:=line.split())==3 and re.fullmatch('[0-9a-fA-F]+',parts[0])}
        irq_stack=symbols['__irq_stack']-symbols['_irq_stack_end'];assert irq_stack==4096
        constants={name:materialized_constants(body) for name,body in bodies.items()
                   if name=='main' or name.startswith('consume')}
        version_hits=[dict(function=name,**item) for name,items in constants.items() for item in items if item['value']==0x12500]
        magic_hits=[dict(function=name,**item) for name,items in constants.items() for item in items if item['value']==0x54465337]
        assert version_hits,'Linked version immediate 0x12500 not found in main/consume'
        assert magic_hits,'Linked descriptor magic immediate 0x54465337 not found in main/consume'
        assert not any(item['value']==0x54465336 for items in constants.values() for item in items),'Old descriptor magic still linked in main/consume'
        attributes=tool('readelf','-A',elf);elf_header=tool('readelf','-h',elf)
        assert re.search(r'Machine:\s+ARM',elf_header) and 'little endian' in elf_header
        assert re.search(r'Tag_ABI_VFP_args:\s+VFP registers',attributes),attributes
        assert re.search(r'Tag_FP_arch:\s+VFPv3',attributes),attributes
        bsp=SDK/'hdmi_platform/ps7_cortexa9_0/standalone_a9/bsp/bsp.yaml'
        assert '-DFPU_HARD_FLOAT_ABI_ENABLED=1' in bsp.read_text()
        user=imported/'UserConfig.cmake';user_text=user.read_text()
        assert 'set(USER_COMPILE_OPTIMIZATION_LEVEL -O2)' in user_text
        assert '-fno-builtin-memcpy' in user_text
        linker=imported/'lscript.ld'
        assert '_IRQ_STACK_SIZE = DEFINED(_IRQ_STACK_SIZE) ? _IRQ_STACK_SIZE : 4096;' in linker.read_text()
        build_config={path.relative_to(ROOT).as_posix():sha(path)
                      for path in (bsp,user,linker,SDK/'build_ethernet.py')}
        (OUT/'firmware_elf_attributes.txt').write_text(elf_header+'\n'+attributes,encoding='utf-8')
        result.update(passed=True,firmware_version=0x12500,descriptor_magic=0x54465337,
            source_changes=changes,source_sha256=source_hashes,authored_imported_sources_match=True,
            native_proof_sha256=sha(OUT/'firmware_native_summary.json'),native_counts=native['counts'],
            hardware_sha256=hardware,xsa_embedded_bit_sha256=embedded,new_bit_xsa_elf=True,
            elf_sha256=elf_sha,elf_version_immediates=version_hits,elf_magic_immediates=magic_hits,
            irq_fp_saved=True,irq_stack_bytes=irq_stack,integer_memcpy_preserved=True,
            hard_float_abi=True,bsp_fpu_macro=True,optimization='-O2',fno_builtin_memcpy=True,
            build_config_sha256=build_config,irq_instructions=irq,
            backup_sha256=plan['backup_sha256'],baseline_manifest_sha256=plan['baseline_manifest_sha256'],
            audit_script_sha256=sha(Path(__file__)))
    except Exception:
        result['error']=traceback.format_exc();raise
    finally:
        result['finished_utc']=datetime.now(timezone.utc).isoformat()
        (OUT/'firmware_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:result[key] for key in ('passed','firmware_version','descriptor_magic','elf_sha256',
          'authored_imported_sources_match','new_bit_xsa_elf','irq_fp_saved','irq_stack_bytes','integer_memcpy_preserved')}))


if __name__=='__main__':main()
