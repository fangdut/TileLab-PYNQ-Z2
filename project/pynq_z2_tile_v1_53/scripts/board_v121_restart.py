"""Abrupt host exit + actual JTAG reload tests; no physical power-cycle claim."""
from pathlib import Path
import sys,os,json,time,subprocess,hashlib,shutil
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
from workstation import Station,EthernetBridge,Records
from tcp_transport import EventTCP
from board_v18_continuous import action,wait_idle
OUT=R/'reports/v132/restart';OUT.mkdir(parents=True,exist_ok=True)

def wait(fn,seconds=15):
    end=time.monotonic()+seconds
    while not fn():
        if time.monotonic()>end:raise TimeoutError('Restart acceptance did not complete')
        time.sleep(.05)

def child(mode,root):
    class CrashBridge(EthernetBridge):
        def ack(self,frame):
            if mode=='after_ack':super().ack(frame)
            os._exit(74 if mode=='after_ack' else 73)
    s=Station(root,CrashBridge('169.254.200.10'));s.action(dict(op='capture'))
    deadline=time.monotonic()+40;last_error=''
    while time.monotonic()<deadline:
        if s.error:
            recovery=s.recovery.snapshot(time.monotonic())
            if not recovery['active']:raise RuntimeError(s.error)
            if s.error!=last_error:print(json.dumps(dict(transient=s.error,recovery=recovery)),flush=True);last_error=s.error
        time.sleep(.05)
    raise TimeoutError('Child never reached post-save ACK boundary')

def board_state():
    c=EventTCP('169.254.200.10')
    try:return c.stats()
    finally:c.close()

def ready_board(seconds=25):
    end=time.monotonic()+seconds
    while True:
        try:return board_state()
        except OSError:
            if time.monotonic()>end:raise
            time.sleep(.25)

def case(name,mode,reprogram=False):
    root=OUT/name;root.mkdir(exist_ok=False);before=ready_board();begin=time.monotonic()
    process=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__)), '--child',mode,str(root)],capture_output=True,text=True,timeout=45,creationflags=0x08000000)
    (root/'child.log').write_text(process.stdout+process.stderr,encoding='utf-8')
    assert process.returncode==(74 if mode=='after_ack' else 73),process.stderr
    store=Records(root);pending=store.confirmations.pending();rows=store.all();assert pending and len(rows)==1
    record=rows[0];assert record['pixel_crc_verified'] and record['header_crc_verified'] and record['descriptor_crc_verified']
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'review_records').glob('*.png')}
    store.update(record['id'],'needs_recheck','Restart test evidence: preserve review and pixels');store.db.close()
    after_crash=ready_board();assert after_crash['boot_id']==pending['frame']['boot_id']
    assert after_crash['head']==(pending['frame']['event_id']-(mode!='after_ack'))&0xffffffff
    if reprogram:
        source=R/'reports/programmed_v132.json'
        shutil.copy2(source,root/'program_before.json')
        with (root/'program.log').open('wb') as log:
            result=subprocess.run(['cmd.exe','/d','/c',str(R/(R.name+'.sdk')/'program_ethernet.bat')],cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=0x08000000)
        assert result.returncode==0,'JTAG reload failed; inspect program.log'
        shutil.copy2(source,root/'program_after.json');fresh=ready_board()
        assert fresh['boot_id']!=pending['frame']['boot_id'] and fresh['version']==0x11500
    class CountBridge(EthernetBridge):
        def __init__(self):super().__init__('169.254.200.10');self.ops=[]
        def capture(self,*args):self.ops.append('capture');return super().capture(*args)
        def ack(self,*args):self.ops.append('ack');return super().ack(*args)
        def stats(self):self.ops.append('stats');return super().stats()
    b=CountBridge();s=Station(root,b)
    try:
        assert s.pending_ack and not s.enabled and not s.error
        s.action(dict(op='resume_pending'))
        wait(lambda:not s.busy and not s.retry_requested)
        assert not s.error and s.pending_ack is None and not s.pending_stats and s.captures==0
        status='BOARD_RESTARTED_UNCONFIRMED' if reprogram else 'ALREADY_ACKNOWLEDGED' if mode=='after_ack' else 'ACKNOWLEDGED'
        assert s.records.confirmations.history()[0]['status']==status
        assert b.ops==(['stats','ack','stats'] if status=='ACKNOWLEDGED' else ['stats','stats'])
        assert len(s.records.all())==1 and s.records.all()[0]['note']=='Restart test evidence: preserve review and pixels'
        assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'review_records').glob('*.png')}
        after=dict(s.board_stats)
        if not reprogram:
            assert all(after[k]==before[k] for k in ('gaps','invalid','dropped','ack_errors','descriptor_crc_errors'))
        result=dict(passed=True,name=name,seconds=time.monotonic()-begin,child_exit_code=process.returncode,real_jtag_reload=reprogram,before=before,after_crash=after_crash,after=after,pending=pending,operations=b.ops,host_captures_after_restart=s.captures,saved_records=1,history=s.records.confirmations.history(),image_sha256=hashes,synchronization_warning=s.synchronization_warning)
        (OUT/(name+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(dict(passed=True,name=name,seconds=result['seconds'],operations=b.ops,status=status),ensure_ascii=False),flush=True)
        return result
    finally:s.exit=True;s.worker.join(5);b.close();s.records.db.close()

def run():
    wait_idle();action('display',value='station_6');time.sleep(.5)
    c=EventTCP('169.254.200.10')
    try:
        assert c.stats()['version']==0x11500
        while c.stats()['depth']:
            _,d,m,_=c.capture(89);c.ack(m[2],d[0])
    finally:c.close()
    action('display',value='real_000');time.sleep(.5)
    try:
        cases=[case('host_exit_before_ack','before_ack'),case('host_exit_after_ack','after_ack'),case('board_jtag_restart_with_saved_pending','before_ack',True)]
        summary=dict(passed=True,cases=cases,scope='Actual FPGA/HDMI evidence, abrupt os._exit in isolated host process, actual JTAG BIT+ELF reload; not physical power removal')
        (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print('Three actual restart cases passed',flush=True)
    finally:action('display',value='station_6')

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--child':child(sys.argv[2],Path(sys.argv[3]))
    else:run()
