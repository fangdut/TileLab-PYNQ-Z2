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
    count=0;minimum=127;maximum=-127
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
        count+=size;minimum=min(minimum,min(values));maximum=max(maximum,max(values))
    return dict(weight_bytes=count,minimum=minimum,maximum=maximum,minus128_values=0)


def preflight(hls,regression,profile):
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
    cosim=hls/'solution/sim/report/texture_integer_cosim.rpt'
    if not re.search(r'Verilog\s*\|\s*Pass',cosim.read_text()):
        raise ValueError('RTL co-simulation did not pass')
    xml=ET.parse(hls/'solution/syn/report/texture_integer_csynth.xml')
    resources=xml.find('.//AreaEstimates/Resources')
    dsp=int(resources.findtext('DSP'))
    bram=int(resources.findtext('BRAM_18K'))
    if dsp>220 or bram>280:
        raise ValueError('HLS DSP/BRAM estimate exceeds the target device')
    return dict(scope='OFFLINE_CANDIDATE_PREFLIGHT_NOT_BOARD',source_sha256=sha(source),
        model_sha256=graph['sha256'],c_regression_summary_sha256=sha(regression/'summary.json'),
        rtl_cosim_sha256=sha(cosim),hls_dsp=dsp,hls_bram18=bram,
        centered_packing_weights=packed_weight_proof(source,profile,graph))


def main():
    p=argparse.ArgumentParser()
    for n in ['hls','regression','profile','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--video',action='store_true')
    p.add_argument('--opt-directive',choices=['Default','ExploreArea','ExploreWithRemap'],default='Default')
    a=p.parse_args()
    if not a.out.is_absolute() or a.out.exists():raise ValueError('Fresh absolute hardware output required')
    proof=preflight(a.hls,a.regression,a.profile)
    root=Path(__file__).resolve().parents[2]
    env=os.environ.copy();env['TILE_TEXTURE_HLS']=str(a.hls);env['TILE_TEXTURE_HW']=str(a.out)
    env['TILE_TEXTURE_OPT_DIRECTIVE']=a.opt_directive
    proof['opt_directive']=a.opt_directive
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
