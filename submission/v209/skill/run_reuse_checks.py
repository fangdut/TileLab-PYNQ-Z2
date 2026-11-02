"""Run actual independent fixtures; never accesses a board or modifies sources."""
from pathlib import Path
import argparse,hashlib,json,platform,subprocess,sys,tempfile,zipfile
import numpy as np

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--bundle',type=Path);a=p.parse_args()
    if a.out.exists():raise ValueError('Output must be a new file')
    here=Path(__file__).resolve().parent;checks=[]
    def run(name,script,args,expected_zero,scenario):
        r=subprocess.run([sys.executable,str(here/script),*map(str,args)],capture_output=True,text=True,encoding='utf8')
        passed=(r.returncode==0)==expected_zero
        row=dict(name=name,scenario=scenario,expected_success=expected_zero,exit_code=r.returncode,passed=passed)
        if r.stdout.strip():
            try:row['result']=json.loads(r.stdout.strip().splitlines()[-1])
            except ValueError:row['result']='non_json_output'
        checks.append(row)
        if not passed:raise AssertionError(name+' unexpected result')
    h=lambda b:hashlib.sha256(b).hexdigest()
    with tempfile.TemporaryDirectory(prefix='generic_skill_') as tmp:
        root=Path(tmp)
        # New DSP task, not a TileLab image. Independent integer reference.
        x=np.array([3,-2,5,7,-1,4],dtype=np.int16);taps=[1,2,1]
        ref=np.array([sum(int(x[j])*taps[i-j] for j in range(len(x)) if 0<=i-j<len(taps)) for i in range(len(x)+2)],dtype=np.int32)
        captured=np.convolve(x.astype(np.int32),np.array(taps,dtype=np.int32))
        np.save(root/'ref.npy',ref);np.save(root/'actual.npy',captured)
        base=['--expected',root/'ref.npy','--actual',root/'actual.npy','--out']
        run('dsp_exact','compare_arrays.py',[*base,root/'equal.json'],True,'integer_fir_fixture_no_hardware')
        captured[2]+=1;np.save(root/'actual.npy',captured)
        run('dsp_one_error','compare_arrays.py',[*base,root/'different.json'],False,'integer_fir_fixture_no_hardware')
        np.save(root/'actual.npy',ref.astype(np.int16))
        run('dtype_mismatch','compare_arrays.py',[*base,root/'dtype.json'],False,'integer_fir_fixture_no_hardware')
        np.save(root/'actual.npy',ref.reshape(2,4))
        run('shape_mismatch','compare_arrays.py',[*base,root/'shape.json'],False,'integer_fir_fixture_no_hardware')
        package=root/'packets';package.mkdir();raw=bytes(range(128));(package/'frame.bin').write_bytes(raw)
        records={'files':{'frame.bin':dict(bytes=len(raw),sha256=h(raw))}}
        (package/'manifest.json').write_text(json.dumps(records),encoding='utf8')
        run('packet_manifest_valid','verify_files.py',[package],True,'communication_frame_fixture_no_hardware')
        (package/'frame.bin').write_bytes(bytes([255])+raw[1:])
        run('packet_tamper_rejected','verify_files.py',[package],False,'communication_frame_fixture_no_hardware')
        records={'files':{'../escape.bin':dict(bytes=0,sha256=h(b''))}}
        (package/'manifest.json').write_text(json.dumps(records),encoding='utf8')
        run('escape_path_rejected','verify_files.py',[package],False,'communication_frame_fixture_no_hardware')
        dep=root/'deploy';dep.mkdir();bit=b'synthetic_bit_fixture';(dep/'system.bit').write_bytes(bit)
        with zipfile.ZipFile(dep/'system.xsa','w') as z:z.writestr('system.bit',bit)
        manifest=dep/'deployment.json'
        def deploy_manifest():manifest.write_text(json.dumps({'files':{n:h((dep/n).read_bytes()) for n in ['system.bit','system.xsa']}}),encoding='utf8')
        deploy_manifest()
        run('synthetic_pair_valid','verify_bundle.py',['--root',dep,'--manifest',manifest],True,'synthetic_deployment_fixture_not_real_bit')
        with zipfile.ZipFile(dep/'system.xsa','w') as z:z.writestr('system.bit',b'different_fixture')
        deploy_manifest()
        run('synthetic_pair_mismatch','verify_bundle.py',['--root',dep,'--manifest',manifest],False,'synthetic_deployment_fixture_not_real_bit')
        if a.bundle:
            real=a.bundle.resolve();run('restored_bundle_manifest','verify_files.py',[real],True,'actual_frozen_bundle_files_no_board')
            realhw=real/'verified_hdmi/hardware'
            realmanifest=root/'actual_pair.json';realmanifest.write_text(json.dumps({'files':{n:h((realhw/n).read_bytes()) for n in ['system.bit','system.xsa']}}),encoding='utf8')
            run('actual_xsa_bit_pair','verify_bundle.py',['--root',realhw,'--manifest',realmanifest],True,'actual_frozen_artifact_pair_no_board')
    result=dict(schema='generic_skill_reuse_v1',python_version=platform.python_version(),platform=platform.system(),independent_temporary_directory=True,contexts=['integer_fir','communication_frames','artifact_deployment'],checks=checks,passed=sum(c['passed'] for c in checks),total=len(checks),cross_machine_tested=False,cross_board_deployment_tested=False,pynq_overlay_dma_tested=False,board_operation=False)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(dict(passed=result['passed'],total=result['total'],board_operation=False)))

if __name__=='__main__':main()
