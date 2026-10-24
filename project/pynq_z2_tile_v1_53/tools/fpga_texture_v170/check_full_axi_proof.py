"""Validate explicit complete-AXI proof; never pretend it is HLS co-simulation."""
from pathlib import Path
import hashlib,json,re
def verify(hls,proof_file):
    hls=Path(hls);proof_file=Path(proof_file);base=proof_file.parent
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    p=json.loads(proof_file.read_text());root=Path(__file__).resolve().parents[2]
    if p.get('scope')!='COMPLETE_GENERATED_DETECTOR_AXI_RTL_TWO_LAUNCHES_NOT_BOARD' or not p.get('passed'):raise ValueError('Complete AXI RTL proof required')
    for key in ['results_exact','intermediate_features_exact','second_launch_alarm_and_mask_cleanup']:
        if p.get(key) is not True:raise ValueError('AXI RTL check missing: '+key)
    if p.get('launches')!=2 or p.get('input_width')!=79 or p.get('input_height')!=65:raise ValueError('Unexpected full AXI fixture coverage')
    if p['source_sha256']!=sha(hls/'src/texture_integer.cpp'):raise ValueError('Full AXI RTL source differs')
    actual={f.name:sha(f) for f in sorted((hls/'solution/syn/verilog').glob('*')) if f.suffix in ['.v','.dat']}
    if actual!=p['dut_files']:raise ValueError('Generated RTL/ROM changed after full AXI test')
    if p['test_driver_sha256']!=sha(root/'experimental/paired_conv_v188/test_full_axi.py') or p['axi_memory_sha256']!=sha(root/'experimental/paired_conv_v188/axi_ram_tb.sv'):raise ValueError('AXI test infrastructure changed')
    if p['testbench_sha256']!=sha(base/'tb_full_axi.sv') or p['xsim_log_sha256']!=sha(base/'xsim.log'):raise ValueError('AXI testbench or raw transcript changed')
    names=['test_model.bin','test_rgb.bin','test_expected.bin','test_fa_expected.bin','test_fb_expected.bin']
    if p['fixture']!={n:sha(base/n) for n in names}:raise ValueError('AXI fixture bytes changed')
    checks=2*sum((base/n).stat().st_size//4 for n in names[2:])
    if p['checked_words']!=checks or not p['work_reads'] or not p['work_writes']:raise ValueError('Full AXI coverage incomplete')
    log=(base/'xsim.log').read_text(errors='replace')
    if 'Fatal:' in log or 'Error:' in log or 'cannot be opened for reading' in log:raise ValueError('AXI transcript contains simulation failure')
    for launch in [1,2]:
        if not re.search(fr'FULL_AXI_LAUNCH_PASS launch={launch} ',log):raise ValueError('AXI launch evidence missing')
    match=re.search(r'PAIRED_FULL_AXI_RTL_PASS launches=2 checked=(\d+) cycles=(\d+) work_reads=(\d+) work_writes=(\d+)',log)
    if not match or tuple(map(int,match.groups()))!=(checks,p['simulation_cycles'],p['work_reads'],p['work_writes']):raise ValueError('AXI pass marker differs from proof')
    return dict(scope=p['scope'],proof_sha256=sha(proof_file),source_sha256=p['source_sha256'],launches=2,checked_words=checks,fixture=p['fixture'],all_generated_rtl_and_rom_bound=True,board_programmed=False)
