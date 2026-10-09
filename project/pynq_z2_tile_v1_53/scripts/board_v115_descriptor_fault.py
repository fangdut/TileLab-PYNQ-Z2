"""Actual DDR descriptor corruption, then reload clean release before benchmarks."""
from pathlib import Path
import sys,time,json,subprocess,struct,zlib,shutil
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP
from board_v18_continuous import action,wait_idle
O=R/'reports/v132';W=R/(R.name+'.sdk')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def ready():
    end=time.monotonic()+25
    while True:
        c=EventTCP('169.254.200.10')
        try:return c.stats()
        except OSError:
            if time.monotonic()>end:raise
            time.sleep(.2)
        finally:c.close()
def run():
    assert not (O/'descriptor_fault_raw.json').exists(),'Fault test has already run'
    wait_idle();action('display',value='real_000');time.sleep(.5)
    programmed=read(R/'reports/programmed_v132.json');before=ready()
    assert before['version']==0x10f00 and before['boot_id']==programmed['boot_id']
    shutil.copy2(R/'reports/programmed_v132.json',O/'program_before_descriptor_fault.json')
    try:
        with (O/'descriptor_fault.log').open('wb') as log:
            p=subprocess.run(['cmd.exe','/d','/c','D:/2025.2/Vitis/bin/xsdb.bat',str(R/'scripts/inject_descriptor_fault.tcl'),str(programmed['boot_id'])],cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=0x08000000)
        p.check_returncode();proof=read(O/'descriptor_fault_raw.json');words=list(proof['original_words']);crc=words[8];words[8]=0
        assert zlib.crc32(struct.pack('<40I',*words))==crc
        words[2]=proof['changed_seq'];assert zlib.crc32(struct.pack('<40I',*words))!=crc
        assert proof['after'][37]-proof['before'][37]==1 and proof['changed_seq']==proof['original_seq']^1
        proof['scope']='Actual future completed DMA trailer frame-number bit flipped via JTAG while ARM stopped; deliberately pauses acquisition; not a normal no-gap performance test'
        proof['independent_zlib_verified']=True
    finally:
        # Clear deliberate capture pauses, test counter increments and any
        # finite-ring invalidations by loading the exact same release again.
        with (O/'program_after_fault.log').open('wb') as log:
            reload=subprocess.run(['cmd.exe','/d','/c',str(W/'program_ethernet.bat')],cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=0x08000000)
        reload.check_returncode();action('display',value='station_6')
    after=ready();assert after['version']==0x10f00 and after['boot_id']!=programmed['boot_id']
    assert after['descriptor_crc_errors']==0 and after['invalid']==0 and after['gaps']==0
    proof['clean_restart']=after;proof['program_after']=read(R/'reports/programmed_v132.json')
    (O/'descriptor_fault_summary.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=True,real_descriptor_crc_rejections=1,old_boot=programmed['boot_id'],new_boot=after['boot_id'],clean_counter_reset=True)))
if __name__=='__main__':run()
