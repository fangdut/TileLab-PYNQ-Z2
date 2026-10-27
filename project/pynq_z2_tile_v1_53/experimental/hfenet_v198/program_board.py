"""Verify matching implemented bitstream/BSP/ELF, then volatile JTAG load."""
from pathlib import Path
import argparse,hashlib,json,os,secrets,subprocess,zipfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts/texture_v170"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_reset import verify
from clock_contract import verify as verify_clock
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--hardware',type=Path,required=True);p.add_argument('--software',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('Use new evidence directory')
    result=json.loads((a.software/'BUILD_RESULT.json').read_text());status=json.loads((a.hardware/'implementation_status.json').read_text());verify(a.hardware)
    verify_clock(a.hardware)
    if status['setup_slack_ns']<0 or status['hold_slack_ns']<0 or status['drc_errors']:raise ValueError('Failed timing/DRC')
    if result.get('pl_identity')!=0x19800001 or result['model_capability_proof']['identity']!=0x19800001:raise ValueError('Not HFENet198 firmware')
    preflight=json.loads((a.hardware/'candidate_preflight.json').read_text());assert preflight['identity']==0x19800001 and preflight['model_sha256']==result['model_sha256']
    for name,digest in result['sources'].items():
        if sha(a.software/'sources'/name)!=digest:raise ValueError('Software source changed: '+name)
    elf=a.software/'texture_transport/build/texture_transport.elf'
    for key,file in [('elf_sha256',elf),('xsa_sha256',a.hardware/'system.xsa'),('bit_sha256',a.hardware/'system.bit')]:
        if sha(file)!=result[key]:raise ValueError('Build identity mismatch: '+key)
    with zipfile.ZipFile(a.hardware/'system.xsa') as z:
        names=[n for n in z.namelist() if n.endswith('/ps7_init.tcl') or n=='ps7_init.tcl']
        if len(names)!=1:raise ValueError('Ambiguous PS7 init')
        init=z.read(names[0])
    a.out.mkdir(parents=True);(a.out/'ps7_init.tcl').write_bytes(init)
    boot=secrets.randbelow(0xfffffffe)+1
    def tpath(p):return '{'+p.resolve().as_posix()+'}'
    script='''if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
puts "previous_jtag_clock [jtag frequency]"
if {[jtag frequency 1000000] != 1000000} {error "Could not select 1MHz JTAG clock"}
puts "program_jtag_clock [jtag frequency]"
set inventory [targets]
puts $inventory
if {![regexp {ARM Cortex-A9} $inventory]} {
 targets -set -filter {name == "xc7z020"}
 fpga -file BIT
 after 2000
 disconnect
 connect -url tcp:127.0.0.1:3121
 jtag targets -set 1
 if {[jtag frequency 1000000] != 1000000} {error "Could not select 1MHz JTAG clock"}
 puts "program_jtag_clock [jtag frequency]"
 puts [targets]
}
targets -set -filter {name =~ "ARM*#0"}
puts "stage_reset_begin"
rst -system
after 1000
stop
source INIT
puts "stage_ps_init_begin"
ps7_init
puts "stage_bit_download_begin"
fpga -file BIT
puts "stage_bit_download_done"
ps7_post_config
puts "stage_elf_download_begin"
dow ELF
puts "stage_elf_download_done"
mwr 0x05f00000 [list 0 0 BOOT 0 0 0 0 0]
con
puts "stage_run_done"
after 2000
targets -set -filter {name == "APU"}
loadhw -hw XSA
if {[expr [lindex [mrd -value 0x41200000 1] 0]] != 0x19800001} {error "Wrong PL build identity"}
set ready 0
for {set i 0} {$i<30} {incr i} {
 if {[expr [lindex [mrd -value 0x05f00000 1] 0]] == 0x19800001} {set ready 1;break}
 after 1000
}
if {!$ready} {error "Transport firmware did not start within PHY initialization deadline"}
puts "V198_VOLATILE_LOAD_PASSED"
disconnect
} why opts]} {puts stderr $why;if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]};exit 1}
exit 0
'''
    for k,v in [('INIT',tpath(a.out/'ps7_init.tcl')),('BIT',tpath(a.hardware/'system.bit')),('ELF',tpath(elf)),('BOOT',str(boot)),('XSA',tpath(a.hardware/'system.xsa'))]:script=script.replace(k,v)
    tcl=a.out/'program.tcl';tcl.write_text(script)
    with (a.out/'program.log').open('w') as log:r=subprocess.run([os.environ.get('TILELAB_XSDB','D:/2025.2/Vitis/bin/xsdb.bat'),str(tcl)],stdout=log,stderr=subprocess.STDOUT,timeout=240)
    if r.returncode or 'V198_VOLATILE_LOAD_PASSED' not in (a.out/'program.log').read_text():raise RuntimeError('JTAG startup checks failed; inspect program.log')
    (a.out/'identity.json').write_text(json.dumps(dict(boot_identity=boot,build=result,implementation=status,flash_written=False),indent=2))
    print('Volatile PL+ARM startup checked; now verify real-photo inference over TCP.',flush=True)
if __name__=='__main__':main()
