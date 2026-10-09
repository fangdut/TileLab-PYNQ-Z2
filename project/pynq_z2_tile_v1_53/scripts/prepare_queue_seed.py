"""Derive actual ARM field offsets and prepare a pre-DMA breakpoint injector."""
from pathlib import Path
import subprocess,struct,json,hashlib
R=Path(__file__).resolve().parents[1];W=R/(R.name+'.sdk');O=R/'reports/v132';T=Path('D:/2025.2/Vitis/gnu/aarch32/nt/gcc-arm-none-eabi/bin')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
command=[str(T/'arm-none-eabi-gcc.exe'),'-O2','-mcpu=cortex-a9','-mfpu=vfpv3','-mfloat-abi=hard','-I'+str(W/'ethernet_sources'),'-c',str(R/'diagnostics/queue_layout.c'),'-o',str(O/'queue_layout.o')]
subprocess.run(command,check=True,capture_output=True)
subprocess.run([str(T/'arm-none-eabi-objcopy.exe'),'-O','binary','-j','.queue_layout',str(O/'queue_layout.o'),str(O/'queue_layout.bin')],check=True,capture_output=True)
names=('magic','sizeof','meta','desc','slot_used','head','tail','last_ack','read_pos','write_pos','refs','meta_words','capacity','slots','frame_base','frame_stride','frame_bytes','read_meta_index','write_meta_index')
v=struct.unpack('<19I',(O/'queue_layout.bin').read_bytes());layout=dict(zip(names,v))
assert layout['magic']==0x514c3137 and layout['meta_words']==66 and layout['slots']==48 and layout['capacity']==12
elf=W/'hdmi_ethernet/build/hdmi_ethernet.elf'
nm=subprocess.check_output([str(T/'arm-none-eabi-nm.exe'),'-n',str(elf)],text=True)
symbols={m[2]:int(m[0],16) for l in nm.splitlines() if len(m:=l.split())==3}
layout['queue_address']=symbols['queue'];layout['breakpoint_address']=symbols['tile_network_start']
layout['elf_sha256']=sha(elf);layout['header_sha256']=sha(W/'ethernet_sources/event_queue.h')
(O/'queue_debug_layout.json').write_text(json.dumps(layout,indent=2),encoding='utf-8')
tcl='\n'.join(f'set q_{k} {v}' for k,v in layout.items() if isinstance(v,int))+'\n'
(O/'queue_debug_layout.tcl').write_text(tcl)
original=(W/'program_ethernet.tcl').read_text()
original=original.replace('set ws [file dirname [file normalize [info script]]]',
                         'set root [file normalize [file join [file dirname [info script]] ..]]\nset ws $root/pynq_z2_tile_v1_53.sdk')
prefix='''# Controlled initial state injection into the actual release ELF.
if {[llength $argv]!=2} {error "Need initial head sequence and output proof JSON"}
lassign $argv seed output
if {![string is wideinteger -strict $seed] || $seed<0 || $seed>0xffffffff} {error "Seed outside uint32"}
set argv {}
'''
inject=r'''
source $root/reports/v132/queue_debug_layout.tcl
set breakpoint [bpadd -addr $q_breakpoint_address -type hw]
con -block -timeout 5
bpremove $breakpoint
proc rd {addr} {return [expr [lindex [mrd -value $addr 1] 0]]}
proc words {addr count} {set out {};foreach x [mrd -value $addr $count] {lappend out [expr {$x+0}]};return $out}
if {[rd 0x10000000]!=0x54494c33 || [rd 0x10000004]!=0x11200 || [rd 0x10000008]!=$boot} {error "Breakpoint did not reach initialized V1.18 queue"}
if {[rd 0x10000010]!=0 || [rd 0x10000014]!=0 || [rd 0x10000018]!=0 || [rd 0x10000024]!=0 || [rd 0x10000050]!=0} {error "Queue is not empty or DMA already started"}
if {[rd [expr {$q_queue_address+$q_meta}]]!=0x10000000 || [rd [expr {$q_queue_address+$q_desc}]]!=0x10001000} {error "Actual queue pointers mismatch layout"}
foreach value [words [expr {$q_queue_address+$q_slot_used}] 2] {if {$value!=0} {error "Queue still owns slots"}}
foreach value [words [expr {$q_queue_address+$q_refs}] 12] {if {$value!=0} {error "Queue references not empty"}}
set before [words 0x10000000 66]
set physical [expr {$seed%12}]
foreach offset [list $q_head $q_tail $q_last_ack] {mwr [expr {$q_queue_address+$offset}] $seed}
foreach offset [list $q_read_pos $q_write_pos] {mwr [expr {$q_queue_address+$offset}] $physical}
mwr 0x10000010 [list $seed $seed]
mwr 0x1000002c $seed
mwr 0x10000100 [list $physical $physical]
set after [words 0x10000000 66]
set raw_queue [words $q_queue_address [expr {$q_sizeof/4}]]
set f [open $output w]
puts $f "{\"seed\":$seed,\"physical_start\":$physical,\"boot_id\":$boot,\"before\":\[[join $before ,]\],\"after\":\[[join $after ,]\],\"queue_words\":\[[join $raw_queue ,]\]}"
close $f
'''
assert original.count('\ncon\n')==1
generated=prefix+original.replace('\ncon\n','\n'+inject+'\ncon\n')
(R/'scripts/program_queue_seed.tcl').write_text(generated,encoding='utf-8')
print(json.dumps(layout))
