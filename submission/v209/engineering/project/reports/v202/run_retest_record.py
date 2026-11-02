from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time,urllib.request
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020');B=R/'engineering_delivery_20261027/TileLab_Engineering_V200';out=W/'v202_usb_retest01'
assert out.is_dir() and not (out/'plan.json').exists()
python=sys.executable;xsdb='D:/2025.2/Vitis/bin/xsdb.bat';config=max((B/'runtime').glob('run_*/station_config.json'),key=lambda p:p.stat().st_mtime);run=config.parent
def save(name,data):(out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
def state():
    with urllib.request.urlopen('http://127.0.0.1:8793/api/state',timeout=10) as response:return json.load(response)
initial=state();identity=json.loads((run/'program/identity.json').read_text());boot=identity['boot_identity'];assert initial['connection']['boot_identity']==boot and initial['phase']=='READY' and not initial['closed_loop']['materials']
save('initial.json',initial);save('plan.json',dict(scope='USER_REPLACED_USB_CABLE100MHZ_MATCHED_BASELINE_RETEST_NOT_ELECTRICAL_MEASUREMENT',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),user_reported_usb_cable_replaced=True,board_boot_identity=boot,runtime=str(run),unchanged_bit_sha256=identity['build']['bit_sha256'],unchanged_elf_sha256=identity['build']['elf_sha256'],unchanged_model_sha256=identity['build']['model_sha256'],pl_clock_mhz=100,stages=['clear_old_reset_reason_and_verify_clock','117_original_photos_no_extra_pause','200_requested_fixed_frame_hardware_autorestarts','22_reference_workflows_and38_rejections','100_full_cycles_with250ms_automated_review_hold','verify_no_reset_flags_or_boot_change'],physical_actuation=False,real_human_review=False,independent_accuracy=False))
def clock_script(clear):
    text='''if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
jtag frequency 1000000
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v199_hardware_binding01/system.xsa}
set reason [expr [lindex [mrd -value 0xf8000258 1] 0]]
puts [format "RESET_REASON 0x%08x" $reason]
CLEAR_HISTORY
set clock [expr [lindex [mrd -value 0xf8000170 1] 0]]
puts [format "FCLK0_CONTROL 0x%08x" $clock]
if {($clock & 0x03f03f30) != 0x00200500} {error "Not baseline100MHz divider"}
set observed_boot [expr [lindex [mrd -value 0x05f00008 1] 0]]
puts "BOOT_ID $observed_boot"
if {$observed_boot != BOOT_EXPECTED} {error "Unexpected boot identity"}
puts "CORE_STATUS [mrd -value 0x05f00000 8]"
puts "CLOCK_RESET_CHECK_PASS"
disconnect
} why]} {puts stderr $why;exit 1}
exit 0
'''
    clearing='''mwr 0xf8000008 0xdf0d
mwr 0xf8000258 [expr {$reason & ~0x007f0000}]
mwr 0xf8000004 0x767b
set cleared [expr [lindex [mrd -value 0xf8000258 1] 0]]
puts [format "RESET_BASELINE 0x%08x" $cleared]
if {$cleared & 0x007f0000} {error "Reset history not cleared"}
''' if clear else 'if {$reason & 0x007f0000} {error "A new reset cause was recorded"}'
    return text.replace('CLEAR_HISTORY',clearing).replace('BOOT_EXPECTED',str(boot))
for name,clear in [('before.tcl',True),('after.tcl',False)]:(out/name).write_text(clock_script(clear))
stages=[];started=time.perf_counter();error=None
def execute(name,command,timeout):
    save('running.json',dict(stage=name,command=command,boot_identity=boot,pid=__import__('os').getpid()))
    tick=time.perf_counter()
    with (out/(name+'.log')).open('w',encoding='utf8') as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,check=True)
    stages.append(dict(stage=name,seconds=time.perf_counter()-tick,passed=True));save('stages.json',stages);print('STAGE_PASS',name,flush=True)
try:
    execute('reset_before',[xsdb,str(out/'before.tcl')],40)
    execute('exact117',[python,'-X','utf8',str(P/'tools/fpga_texture_v170/recheck_archive_v199.py'),'--bundle',str(B),'--out',str(out/'exact117'),'--pause','0'],240)
    execute('core200',[python,'-X','utf8',str(W/'v201_core_diagnostic.py'),'--out',str(out/'core200'),'--frames','200','--clock','100'],90)
    execute('workflow22',[python,'-X','utf8',str(P/'host/stop_inspect_station/accept_closed_loop.py'),'--expected',str(W/'v200_catalog01/expected_offline_only.json'),'--profiles',str(W/'v200_profiles03'),'--out',str(out/'workflow22')],150)
    execute('soak100',[python,'-X','utf8',str(P/'host/stop_inspect_station/accept_soak.py'),'--expected',str(W/'v200_catalog01/expected_offline_only.json'),'--runtime',str(run/'station_records'),'--out',str(out/'soak100'),'--cycles','100','--review-hold','.25','--serial','COM20'],240)
    execute('reset_after',[xsdb,str(out/'after.tcl')],40)
    final=state();assert final['connection']['boot_identity']==boot and final['closed_loop']['calibrated'];save('final.json',final)
except Exception as exc:
    error=repr(exc);save('failure.json',dict(error=error,completed_stages=stages))
    try:
        with (out/'failure_probe.log').open('w') as f:subprocess.run([xsdb,str(W/'v201_failure_probe01.tcl')],stdout=f,stderr=subprocess.STDOUT,timeout=40,check=False)
    except Exception as second:save('probe_failure.json',dict(error=repr(second)))
    raise
finally:
    summary=dict(scope='MATCHED100MHZ_RETEST_AFTER_USER_USB_CABLE_CHANGE_NOT_LONG_TERM_OR_INDEPENDENT_ACCURACY',passed=error is None,boot_identity=boot,runtime=str(run),elapsed_seconds=time.perf_counter()-started,stages=stages,error=error,automatic_reprogram_or_inference_retry=False,root_cause_proven=False)
    for stage in ['exact117','core200','workflow22','soak100']:
        file=out/stage/'summary.json'
        if file.is_file():summary[stage]=json.loads(file.read_text())
    save('summary.json',summary);print(json.dumps(summary),flush=True)
