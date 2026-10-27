"""New-network-only gates. Does not weaken any legacy MVTec acceptance gate."""
from pathlib import Path
import argparse,json,hashlib,os,subprocess,re,xml.etree.ElementTree as E
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def preflight(hls,regression,rtl,profile):
    graph=json.loads((profile/'graph.json').read_text());assert graph['kernel_kind']=='HFENET198' and graph['pl_identity']==0x19800001
    assert sha(profile/'model.bin')==graph['sha256']
    c=json.loads((regression/'summary.json').read_text());r=json.loads((rtl/'summary.json').read_text());assert c['cases']==80 and c['all72_tensors_each_image_exact'] and c['all_masks_exact'] and not c['board_verified'];assert c['model_sha256']==graph['sha256']
    assert r['passed'] and r['valid_launches']==2 and r['transactions']==4 and r['all_retained72_tensors_exact']
    transcript=(rtl/'xsim.log').read_text(errors='replace')
    matches=re.findall(r'HFE_COMPLETE_AXI_PASS checked=(\d+) cycles=(\d+) reads=(\d+) writes=(\d+)',transcript)
    # Xsim's own logger and captured console may repeat identical final lines.
    # Require one unique completion tuple and both unique validated launches.
    assert len(set(matches))==1 and 'Fatal:' not in transcript and 'ERROR:' not in transcript
    assert int(matches[0][0])==r['checked_words']==49826 and int(matches[0][1])==r['simulation_cycles']
    launches=set(re.findall(r'HFE_LAUNCH_PASS launch=([12]) cycle=(\d+) checked=(\d+)',transcript))
    assert len(launches)==2 and {x[0] for x in launches}=={'1','2'}
    assert {x[2] for x in launches}=={'24913','49826'}
    for name,digest in r['fixture'].items():
        wordbytes=8 if name.startswith(('model','work')) else 4
        values=(rtl/(Path(name).stem+'.mem')).read_text().split()
        decoded=b''.join(int(v,16).to_bytes(wordbytes,'little') for v in values)
        assert hashlib.sha256(decoded).hexdigest()==digest,name
    components={name:sha(hls/'src'/name) for name in ['texture_integer.cpp','norm_math.hpp','contract.hpp']}
    assert components==r['source_components'];assert all(c['source_binding']['sources'][name]==value for name,value in components.items())
    for name,value in r['dut_files'].items():assert sha(hls/'solution/syn/verilog'/name)==value
    root=Path(__file__).resolve().parent
    for name,value in components.items():assert sha(root/name)==value
    assert sha(root/'test_axi.py')==r['driver_sha256'] and sha(root/'axi_ram_tb.sv')==r['axi_ram_sha256']
    x=E.parse(hls/'solution/syn/report/texture_integer_csynth.xml').getroot();resources={k:int(x.findtext('.//AreaEstimates/Resources/'+k)) for k in ['DSP','BRAM_18K','LUT','FF']};period=float(x.findtext('.//EstimatedClockPeriod'))
    assert resources['DSP']<=220 and resources['BRAM_18K']<=280 and period<=18.001
    # HLS area is an estimate. The Tcl additionally gates actual whole-system
    # synthesis capacity before spending time on place-and-route.
    ip=hls/'solution/impl/ip';assert (ip/'component.xml').is_file()
    packaged=ip/'hdl/verilog'
    for f in (hls/'solution/syn/verilog').glob('*.v'):
        assert (packaged/f.name).is_file() and (packaged/f.name).read_bytes()==f.read_bytes(),f.name
    return dict(scope='HFENET198_FULL_C_AND_COMPLETE_AXI_RTL_PREFLIGHT_NOT_BOARD',source_sha256=components['texture_integer.cpp'],source_components=components,model_sha256=graph['sha256'],full_c_summary_sha256=sha(regression/'summary.json'),rtl_summary_sha256=sha(rtl/'summary.json'),rtl_transcript_sha256=sha(rtl/'xsim.log'),testbench_sha256=sha(rtl/'tb_hfe.sv'),hls_resources_estimates=resources,hls_estimated_period_ns=period,hls_target_clock_ns=20,requested_pl_clock_mhz=50,identity=0x19800001,video=False)
def main():
    p=argparse.ArgumentParser()
    for name in ['hls','regression','rtl','profile','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert a.out.is_absolute() and not a.out.exists();proof=preflight(a.hls,a.regression,a.rtl,a.profile)
    env=os.environ.copy();env.update(TILE_TEXTURE_HW=str(a.out),TILE_TEXTURE_HLS=str(a.hls),TILE_TEXTURE_PL_CLOCK_MHZ='50',TILE_TEXTURE_COMPLETE_AXI_PROOF=str(a.rtl/'summary.json'),TILE_TEXTURE_MEMORY_LAYOUT='shared',TILE_TEXTURE_OPT_DIRECTIVE='Default',TILE_TEXTURE_VIDEO_VARIANT='serial');env.pop('TILE_TEXTURE_VIDEO',None);env.pop('TILE_TEXTURE_PREPARE_ONLY',None)
    log=a.out.with_name(a.out.name+'_console.log')
    with log.open('w') as f:result=subprocess.run(['D:/2025.2/Vivado/bin/vivado.bat','-mode','batch','-source',str(Path(__file__).with_name('build_hardware.tcl')),'-notrace','-nolog','-nojournal'],env=env,stdout=f,stderr=subprocess.STDOUT)
    if a.out.exists():(a.out/'candidate_preflight.json').write_text(json.dumps(proof,indent=2),encoding='utf8')
    if result.returncode:raise RuntimeError('Physical build rejected; see '+str(log))
    status=json.loads((a.out/'implementation_status.json').read_text());assert status['setup_slack_ns']>=0 and status['hold_slack_ns']>=0 and status['drc_errors']==0 and status['pl_clock_mhz']==50
    print(json.dumps(dict(scope='HFENET198_TIMING_CLOSED_NOT_PROGRAMMED',**status)),flush=True)
if __name__=='__main__':main()
