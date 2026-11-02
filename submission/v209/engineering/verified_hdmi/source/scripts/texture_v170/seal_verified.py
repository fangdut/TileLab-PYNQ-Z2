"""Bind all 117 physical results to matching frozen source/BIT/XSA/ELF/model."""
from pathlib import Path
import argparse,json,hashlib,struct,zlib,shutil,re
import numpy as np
from verify_reset import verify

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf8'))
def main():
    p=argparse.ArgumentParser()
    for n in ['hardware','software','hls','model','program','validation','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();hw=load(a.hardware/'implementation_status.json');build=load(a.software/'BUILD_RESULT.json');program=load(a.program/'identity.json');model=load(a.model/'graph.json');summary=load(a.validation/'summary.json');auto=load(a.validation/'autorestart_benchmark.json')
    verify(a.hardware)
    if min(hw['setup_slack_ns'],hw['hold_slack_ns'])<0 or hw['drc_errors']:raise ValueError('Failed implementation')
    for key,file in [('bit_sha256',a.hardware/'system.bit'),('xsa_sha256',a.hardware/'system.xsa'),('elf_sha256',a.software/'texture_transport/build/texture_transport.elf')]:
        if sha(file)!=build[key] or build[key]!=program['build'][key]:raise ValueError('Programmed build mismatch')
    source=a.hls/'src/texture_integer.cpp';cosim=a.hls/'solution/sim/report/texture_integer_cosim.rpt'
    if source.read_bytes()!=(a.hardware/'texture_integer_source.cpp').read_bytes() or not re.search(r'Verilog\s*\|\s*Pass',cosim.read_text()):raise ValueError('Missing source/RTL proof')
    if sha(a.model/'model.bin')!=model['sha256'] or build['model_sha256']!=model['sha256']:raise ValueError('Model mismatch')
    progress=load(a.validation/'progress.json');cases=[]
    if len(progress)!=117 or summary['correct']!=117 or not summary['all_integer_outputs_exact']:raise ValueError('Historical benchmark failed')
    for r in progress:
        folder=a.validation/r['id'];e=load(folder/'evidence.json');raw=(folder/'raw_result.bin').read_bytes();header=struct.unpack('<16I',raw[:64])
        if e['boot_identity']!=program['boot_identity'] or e['pl_identity']!=0x17000001 or e['model_crc32']!=model['crc32'] or e['cpu_detection'] or e['gpu_detection']:raise ValueError('Invalid physical identity')
        if header[8]!=model['steps'] or header[9]!=r['frame_sequence'] or zlib.crc32(raw)!=e['result_crc32'] or sha(folder/'raw_result.bin')!=e['result_sha256']:raise ValueError('Invalid graph completion/result CRC')
        values=np.frombuffer(raw,dtype='<u4');g=model['grid'];expected=np.load(a.model/(r['id']+'_scores.npy'))
        if np.any(values[16:16+g*g].reshape(g,g)!=expected) or r['mask_mismatches'] or r['max_grid_error']:raise ValueError('Numerical mismatch')
        cases.append(dict(**r,input_file_sha256=e['input_file_sha256'],rgb_crc32=e['rgb_crc32'],result_sha256=e['result_sha256']))
    if auto['boot_identity']!=program['boot_identity'] or not auto['hardware_auto_restart'] or auto['arm_start_writes']!=1:raise ValueError('Invalid auto-restart evidence')
    a.out.mkdir(parents=True,exist_ok=False)
    result=dict(status='PHYSICAL_ALL_INTEGER_BENCHMARK_PASSED_NOT_REALTIME',scope='Exposed historical MVTec Tile benchmark only',
        implementation=hw,programmed_build=build,hls_source_sha256=sha(source),model_sha256=model['sha256'],summary=summary,
        autorestart_fixed_frame=auto,independent_blind_test=False,hdmi_continuous_verified=False,competition_final_acceptance=False,
        pc_runtime=['file decode','RGB packing','transport','display'],arm_runtime=['TCP','CRC','buffer ownership','start/stop','timing'],
        pl_runtime=['integer resize/normalization','all CNN layers','pooling','projection','nearest-normal search','smoothing','alarm','mask'],
        limitations=['Real-time target 10 FPS not yet reached','Repeated fixed DDR frame is not continuous video throughput','Arbitrary painted/mixed materials remain unvalidated','Crack masks are coarse: historical mean IoU approximately 0.067'],cases=cases)
    (a.out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    for n,path in [('timing_summary.rpt',a.hardware/'timing_summary.rpt'),('utilization.rpt',a.hardware/'utilization.rpt'),('hls_cosim.rpt',cosim)]:shutil.copy2(path,a.out/n)
    print(json.dumps(dict(status=result['status'],cases=117,fps=auto['sustained_pl_fps'],source_sha256=sha(source))),flush=True)
if __name__=='__main__':main()
