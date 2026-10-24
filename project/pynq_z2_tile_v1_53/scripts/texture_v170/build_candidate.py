"""Build a fresh candidate only after matching full C and RTL evidence.

This does not program hardware or promote the result to a verified release.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,struct,subprocess
import xml.etree.ElementTree as ET


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def packed_weight_proof(source,profile,graph):
    if b'Signed low packing avoids' not in source.read_bytes():return None
    blob=(profile/'model.bin').read_bytes()
    header=struct.unpack_from('<64I',blob)
    if header[2]!=len(graph['tasks']):raise ValueError('Model task count mismatch')
    count=0;minimum=127;maximum=-127;accumulator_bound=0;active_channels=0;dead_channels=0
    for i,t in enumerate(graph['tasks']):
        if list(struct.unpack_from('<24I',blob,(64+i*24)*4))!=t:
            raise ValueError('Graph and binary task descriptors differ')
        if t[0] not in (1,2):continue
        groups=(t[10]+15)//16
        size=groups*t[11]*t[11]*(16 if t[0]==2 else ((t[9]+7)//8)*128)
        start=t[4]*8
        if start+size>len(blob):raise ValueError('Convolution weights exceed model')
        values=struct.unpack_from('<'+str(size)+'b',blob,start)
        if -128 in values:raise ValueError('Centered packing rejects -128 weights')
        taps=t[11]*t[11]*(1 if t[0]==2 else (t[9]+7)//8)
        sums=[0]*(groups*16)
        for index,value in enumerate(values):
            channel=(index//(taps*16))*16+index%16 if t[0]==2 else (index//(taps*128))*16+(index//8)%16
            sums[channel]+=abs(value)
        bias=struct.unpack_from('<'+str(t[10])+'i',blob,t[5]*4)
        multiplier=struct.unpack_from('<'+str(t[10])+'I',blob,t[6]*4)
        for channel in range(t[10]):
            if multiplier[channel]:
                accumulator_bound=max(accumulator_bound,127*sums[channel]+abs(bias[channel]))
                active_channels+=1
            else:dead_channels+=1
        count+=size;minimum=min(minimum,min(values));maximum=max(maximum,max(values))
    if accumulator_bound>=(1<<23):raise ValueError('Active convolution accumulator exceeds signed24 range')
    return dict(weight_bytes=count,minimum=minimum,maximum=maximum,minus128_values=0,
        active_accumulator_magnitude_bound=accumulator_bound,exclusive_accumulator_limit=1<<23,
        active_channels=active_channels,zero_multiplier_channels=dead_channels)


def preflight(hls,regression,profile,full_axi_proof=None):
    summary=json.loads((regression/'summary.json').read_text())
    graph=json.loads((profile/'graph.json').read_text())
    source=hls/'src/texture_integer.cpp'
    if summary.get('scope')!='OFFLINE_HLS_C_ALL_117_NOT_BOARD':
        raise ValueError('Full integer C regression required')
    if summary['cases']!=117 or not summary['all_grid_values_exact'] or not summary['all_original_size_masks_exact']:
        raise ValueError('Complete exact 117-photo regression required')
    if summary['source_sha256']!=sha(source):
        raise ValueError('C regression and synthesized HLS source differ')
    if summary['model_sha256']!=sha(profile/'model.bin') or graph['sha256']!=summary['model_sha256']:
        raise ValueError('C regression model provenance mismatch')
    root=Path(__file__).resolve().parents[2]
    frozen=root/'experimental/texture_v170/hls/frozen'/(hls.name+'.cpp')
    if not frozen.exists() or frozen.read_bytes()!=source.read_bytes():
        raise ValueError('A byte-exact named source snapshot is required')
    import sys
    sys.path.insert(0,str(root/'tools/fpga_texture_v170'))
    from check_mac_recurrence import inspect as inspect_recurrence
    from check_direct_cache import inspect as inspect_direct_cache
    from check_spatial_coordinates import inspect as inspect_spatial_coordinates
    from check_operation_decode import inspect as inspect_operation_decode
    from check_row_address import inspect as inspect_row_address
    from check_quarter_pipeline import inspect as inspect_quarter_pipeline
    from check_normal_cache import inspect as inspect_normal_cache
    cache_bounds=inspect_direct_cache(source,profile)
    spatial_bounds=inspect_spatial_coordinates(source,profile)
    operation_decode=inspect_operation_decode(hls)
    row_address=inspect_row_address(hls)
    quarter_pipeline=inspect_quarter_pipeline(hls)
    normal_cache=inspect_normal_cache(hls)
    recurrence=inspect_recurrence(hls)
    if not recurrence['all_banks_safe']:
        raise ValueError('Generated MAC feedback is later than its same-slot recurrence')
    cosim=hls/'solution/sim/report/texture_integer_cosim.rpt'
    custom_axi=None
    if full_axi_proof is None:
        if not re.search(r'Verilog\s*\|\s*Pass',cosim.read_text()):
            raise ValueError('RTL co-simulation did not pass')
    else:
        from check_full_axi_proof import verify as verify_full_axi
        custom_axi=verify_full_axi(hls,full_axi_proof)
    xml=ET.parse(hls/'solution/syn/report/texture_integer_csynth.xml')
    resources=xml.find('.//AreaEstimates/Resources')
    dsp=int(resources.findtext('DSP'))
    bram=int(resources.findtext('BRAM_18K'))
    if dsp>220 or bram>280:
        raise ValueError('HLS DSP/BRAM estimate exceeds the target device')
    return dict(scope='OFFLINE_CANDIDATE_PREFLIGHT_NOT_BOARD',source_sha256=sha(source),
        model_sha256=graph['sha256'],c_regression_summary_sha256=sha(regression/'summary.json'),
        rtl_cosim_sha256=sha(cosim) if custom_axi is None else None,complete_axi_rtl=custom_axi,hls_dsp=dsp,hls_bram18=bram,mac_recurrence=recurrence,direct_cache_bounds=cache_bounds,spatial_coordinate_bounds=spatial_bounds,
        centered_packing_weights=packed_weight_proof(source,profile,graph),operation_decode=operation_decode,row_address=row_address,quarter_pipeline=quarter_pipeline,normal_cache=normal_cache)


def main():
    p=argparse.ArgumentParser()
    for n in ['hls','regression','profile','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--video',action='store_true')
    p.add_argument('--video-variant',choices=['serial','overlap_v175'],default='serial')
    p.add_argument('--video-rtl-gate',type=Path)
    p.add_argument('--full-axi-proof',type=Path)
    p.add_argument('--clock-mhz',type=int,choices=[100,125],default=100)
    p.add_argument('--opt-directive',choices=['Default','ExploreArea','ExploreWithRemap'],default='Default')
    p.add_argument('--memory-layout',choices=['shared','split'],default='shared')
    a=p.parse_args()
    if not a.out.is_absolute() or a.out.exists():raise ValueError('Fresh absolute hardware output required')
    proof=preflight(a.hls,a.regression,a.profile,a.full_axi_proof)
    root=Path(__file__).resolve().parents[2]
    if a.video_variant!='serial':
        if not a.video or not a.video_rtl_gate:raise ValueError('Overlap video requires a source-bound RTL gate')
        import importlib.util
        base=root/'experimental/video_overlap_v175'
        spec=importlib.util.spec_from_file_location('overlap_rtl_gate',base/'check_rtl_gate.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        gate=module.inspect(a.video_rtl_gate,base)
        proof['video_rtl_sources']=gate['rtl_sources']
        proof['video_rtl_gate_sha256']=sha(a.video_rtl_gate)
    proof['video_variant']=a.video_variant
    clock_xml=ET.parse(a.hls/'solution/syn/report/texture_integer_csynth.xml').getroot()
    hls_period=float(clock_xml.findtext('UserAssignments/TargetClockPeriod'))
    if hls_period>1000/a.clock_mhz+1e-6:
        raise ValueError('HLS must be rescheduled for the requested faster PL clock')
    proof['requested_pl_clock_mhz']=a.clock_mhz
    proof['hls_target_clock_ns']=hls_period
    env=os.environ.copy();env['TILE_TEXTURE_HLS']=str(a.hls);env['TILE_TEXTURE_HW']=str(a.out)
    env['TILE_TEXTURE_PL_CLOCK_MHZ']=str(a.clock_mhz)
    env['TILE_TEXTURE_VIDEO_VARIANT']=a.video_variant
    env['TILE_TEXTURE_OPT_DIRECTIVE']=a.opt_directive
    proof['opt_directive']=a.opt_directive
    env['TILE_TEXTURE_MEMORY_LAYOUT']=a.memory_layout
    if a.full_axi_proof:env['TILE_TEXTURE_COMPLETE_AXI_PROOF']=str(a.full_axi_proof.resolve())
    else:env.pop('TILE_TEXTURE_COMPLETE_AXI_PROOF',None)
    proof['memory_layout']=a.memory_layout
    if a.video:env['TILE_TEXTURE_VIDEO']='1'
    else:env.pop('TILE_TEXTURE_VIDEO',None)
    env.pop('TILE_TEXTURE_PREPARE_ONLY',None)
    log=a.out.with_name(a.out.name+'_console.log')
    print(json.dumps(proof),flush=True)
    with log.open('w') as f:
        run=subprocess.run(['D:/2025.2/Vivado/bin/vivado.bat','-mode','batch','-source',
            str(root/'scripts/texture_v170/build_hardware.tcl'),'-notrace','-nolog','-nojournal'],
            cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
    if a.out.exists():(a.out/'candidate_preflight.json').write_text(json.dumps(proof,indent=2)+'\n')
    if run.returncode:raise RuntimeError('Candidate build failed; inspect '+str(log))
    status=json.loads((a.out/'implementation_status.json').read_text())
    if status['setup_slack_ns']<0 or status['hold_slack_ns']<0 or status['drc_errors']:
        raise RuntimeError('Physical timing/DRC rejected')
    print(json.dumps(dict(scope='TIMING_CLOSED_NOT_PROGRAMMED',hardware=str(a.out),**status)),flush=True)


if __name__=='__main__':main()
