"""Seal initial board migration evidence, never promote offline accuracy."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,zlib,struct
from verify_reset import verify
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf8'))
def main():
    p=argparse.ArgumentParser()
    for name in ('hardware','software','hls','model','program','validation','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[2]
    implementation=load(a.hardware/'implementation_status.json');build=load(a.software/'BUILD_RESULT.json');program=load(a.program/'identity.json');model=load(a.model/'graph.json');checks=load(a.validation/'summary.json');verify(a.hardware)
    if any(implementation[k]<0 for k in ('setup_slack_ns','hold_slack_ns')) or implementation['drc_errors']:raise RuntimeError('Failed hardware')
    cosim=(a.hls/'solution/sim/report/texture_infer_cosim.rpt').read_text()
    if not re.search(r'Verilog\s*\|\s*Pass',cosim):raise RuntimeError('Failed RTL co-simulation')
    source=root/'experimental/texture_v169/hls/texture_infer.cpp'
    if source.read_bytes()!=(a.hls/'src/texture_infer.cpp').read_bytes() or source.read_bytes()!=(a.hardware/'texture_infer_source.cpp').read_bytes():raise RuntimeError('Changed HLS source')
    for key,file in [('xsa_sha256',a.hardware/'system.xsa'),('bit_sha256',a.hardware/'system.bit'),('elf_sha256',a.software/'texture_transport/build/texture_transport.elf')]:
        if sha(file)!=build[key] or build[key]!=program['build'][key]:raise RuntimeError('Mismatched programmed build')
    if sha(a.model/'model.bin')!=model['sha256'] or build['model_sha256']!=model['sha256']:raise RuntimeError('Mismatched model')
    if checks['cases']!=2 or not checks['all_alarms_match'] or checks['max_grid_error']>1e-3:raise RuntimeError('Failed initial board cases')
    evidence=[]
    for check in checks['cases_details']:
        folder=a.validation/check['id'];e=load(folder/'evidence.json');wire=(folder/'raw_result.bin').read_bytes();h=struct.unpack('<16I',wire[:64])
        if e['scope']!='BOARD_FULL_PL_INFERENCE' or e['boot_identity']!=program['boot_identity'] or e['model_crc32']!=model['crc32'] or e['pl_identity']!=0x16900001 or h[8]!=59:raise RuntimeError('Invalid board identity/completed graph')
        if sha(folder/'raw_result.bin')!=e['result_sha256'] or zlib.crc32(wire)!=e['result_crc32']:raise RuntimeError('Corrupt evidence')
        evidence.append(dict(**check,boot_identity=e['boot_identity'],input_file_sha256=e['input_file_sha256'],rgb_crc32=e['rgb_crc32'],model_crc32=e['model_crc32'],result_crc32=e['result_crc32']))
    a.out.mkdir(parents=True,exist_ok=True)
    result=dict(version='V169',status='INITIAL_FULL_PL_MIGRATION_PASSED',scope='Two real-photo board cases; not complete competition acceptance or full benchmark',
        part='xc7z020clg400-1',implementation=implementation,programmed_build=build,hls_source_sha256=sha(source),model_sha256=model['sha256'],cases=evidence,
        pc_runtime=['image file decoding','RGB packing','TCP transport','display','evidence saving'],ps_runtime=['TCP','CRC','buffer ownership','accelerator start/poll'],pl_runtime=model['pl_computes'],
        cpu_or_gpu_detection_fallback=False,hdmi_integrated=False,offline_historical_benchmark=load(a.model/'summary.json'),
        limitations=['Board cases are an initial normal/crack numerical migration check, not a 117-image board accuracy measurement','MVTec Tile material only; arbitrary painted/mixed materials and walls unvalidated','FP32 large network is not real-time; use measured per-image latency'])
    (a.out/'acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    for name,path in [('hls_cosim.rpt',a.hls/'solution/sim/report/texture_infer_cosim.rpt'),('timing_summary.rpt',a.hardware/'timing_summary.rpt'),('utilization.rpt',a.hardware/'utilization.rpt'),('clocks.rpt',a.hardware/'clocks.rpt')]:shutil.copy2(path,a.out/name)
    print(json.dumps(dict(status=result['status'],cases=evidence),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
