"""Independent V197 integer oracle vs full C-source frame engine."""
from pathlib import Path
import argparse,hashlib,json,sys,contextlib,io,ctypes,subprocess,time,os
import numpy as np,torch
from PIL import Image

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args):
    args.out.mkdir(exist_ok=False);root=Path(__file__).resolve().parent;sys.path[:0]=[str(root.parent/'hfenet_v197'),str(root.parent/'hfenet_v197/vendor')]
    from integer_reference import IntegerGraph,QT
    from preprocess_reference import packed_channels
    from hfenet import HFENet
    torch.set_num_threads(8);meta=json.loads((args.model/'graph.json').read_text());gold=json.loads((args.model/'gold_metadata.json').read_text());program=gold['source'];cal=json.loads((args.integer/'calibration_frozen.json').read_text());qw=np.load(args.model/'gold_weights.npz',allow_pickle=False)
    with contextlib.redirect_stdout(io.StringIO()):net=HFENet()
    graph=torch.fx.symbolic_trace(net);byname={n.name:n for n in graph.graph.nodes};ops={o['name']:o for o in program['operators']}
    for name,settings in gold['normalization'].items():
        m=graph.get_submodule(byname[name].target);m.weight.data=torch.tensor(settings['gamma_q30']).float()/2**30;m.bias.data=torch.tensor(settings['beta_q30']).float()/2**30
    graph.eval();expected_hashes={};expected_tensors={};names=[t['name'] for t in program['tensors']]
    class Oracle(IntegerGraph):
        def run_node(self,node):
            out=super().run_node(node)
            if isinstance(out,QT) and node.op!='output':
                values=out.q.numpy().astype('<i2');expected_hashes[node.name]=hashlib.sha256(values.tobytes()).hexdigest()
                if meta['retained_fixture']:expected_tensors[node.name]=values.copy()
            return out
    oracle=Oracle(graph,cal)
    for name in oracle.weights:oracle.weights[name]=(torch.from_numpy(qw[name].astype('i8')),ops[name]['weight_exponents'])
    if args.image:
        rgb=np.asarray(Image.open(args.image).convert('RGB'));assert rgb.shape==(meta['height'],meta['width'],3);assert np.array_equal(rgb[:,:,0],rgb[:,:,1]) and np.array_equal(rgb[:,:,1],rgb[:,:,2]);gray=rgb[:,:,0]
    else:gray=np.random.default_rng(198).integers(0,256,(meta['height'],meta['width']),dtype='u1');rgb=np.repeat(gray[:,:,None],3,axis=2)
    packed=packed_channels(gray)
    channels=np.stack([(packed>>16)&255,(packed>>8)&255,packed&255],axis=0).astype('f4')[None]
    started=time.perf_counter()
    with torch.inference_mode():expected=oracle.run(torch.from_numpy(channels)).q.numpy()[0,0].astype('u4')
    reference_seconds=time.perf_counter()-started
    source=root/'texture_integer.cpp';dll=args.compiled or args.out/'frame.dll'
    if not args.compiled:
        snapshot=args.out/'source';snapshot.mkdir()
        components=['texture_integer.cpp','native_wrapper.cpp','norm_math.hpp','contract.hpp']
        for name in components:(snapshot/name).write_bytes((root/name).read_bytes())
        command=['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O3','-march=native','-std=c++17','-shared','-static-libgcc','-static-libstdc++','-Wno-unknown-pragmas','-I','D:/2025.2/Vitis/include',str(snapshot/'texture_integer.cpp'),str(snapshot/'native_wrapper.cpp'),'-o',str(dll)]
        with (args.out/'compile.log').open('w') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
        dll.with_suffix('.json').write_text(json.dumps(dict(sources={n:sha(root/n) for n in components},dll_sha256=sha(dll)),indent=2),encoding='utf8')
    proof=json.loads(dll.with_suffix('.json').read_text());assert sha(dll)==proof['dll_sha256'];assert all(sha(root/name)==digest for name,digest in proof['sources'].items())
    dependency_path=os.add_dll_directory('D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin')
    library=ctypes.CDLL(str(dll));ptr=ctypes.c_void_p;callback_t=ctypes.CFUNCTYPE(None,ctypes.c_uint,ptr,ctypes.c_uint,ctypes.c_uint);actual_hashes={};errors=[]
    def capture(ident,pointer,offset,count):
        values=np.ctypeslib.as_array(ctypes.cast(pointer,ctypes.POINTER(ctypes.c_uint64)),shape=(meta['workspace_bytes']//8,)).view('i2')[offset:offset+count]
        actual_hashes[names[ident]]=hashlib.sha256(values.tobytes()).hexdigest()
        if actual_hashes[names[ident]]!=expected_hashes[names[ident]]:
            errors.append(names[ident]);np.save(args.out/(str(ident)+'_actual.npy'),values)
    callback=callback_t(capture);library.tile_observer.argtypes=[callback_t];library.tile_observer(callback);library.tile_run.argtypes=[ptr,ptr,ptr,ptr,ctypes.c_uint,ctypes.c_uint]
    model=np.fromfile(args.model/'model.bin',dtype='<u8');work=np.full(meta['workspace_bytes']//8,0xcccccccccccccccc,dtype='u8');wire=((rgb[:,:,0].astype('u4')<<16)|(rgb[:,:,1].astype('u4')<<8)|rgb[:,:,2].astype('u4')).astype('<u4');result=np.full(17+gray.size,0xdeadbeef,dtype='u4')
    started=time.perf_counter();library.tile_run(model.ctypes.data,work.ctypes.data,wire.ctypes.data,result.ctypes.data,meta['width'],meta['height']);c_seconds=time.perf_counter()-started
    result.tofile(args.out/'actual_result.bin');wire.tofile(args.out/'rgb.bin');np.save(args.out/'expected_mask.npy',expected)
    if expected_tensors:
        for i,name in enumerate(names):expected_tensors[name].tofile(args.out/(str(i)+'_expected.bin'))
        expected_work=np.full(meta['workspace_bytes']//2,0xcccc,dtype='<u2')
        allocation=json.loads((args.model/'allocation.json').read_text())
        for t in allocation['tensors']:
            values=expected_tensors[t['name']].view('u2').ravel();expected_work[t['offset16']:t['offset16']+len(values)]=values
        expected_work.tofile(args.out/'expected_work.bin')
    summary=dict(scope='FULL_FRAME_HLS_SOURCE_C_VS_INDEPENDENT_INTEGER_REFERENCE_NOT_BOARD',source_sha256=sha(source),model_sha256=sha(args.model/'model.bin'),geometry=[meta['width'],meta['height']],synthetic=meta['synthetic_weights'],expected_tensor_count=len(expected_hashes),actual_tensor_count=len(actual_hashes),all_tensor_values_exact=not errors and expected_hashes==actual_hashes,first_mismatches=errors[:5],result_status=int(result[1]),error_location=list(map(int,result[10:12])),completed_steps=int(result[8]),positive_pixels=int(result[6]),mask_exact=bool(np.array_equal(result[17:].reshape(gray.shape),expected)),offline_reference_seconds=reference_seconds,offline_c_seconds=c_seconds,board_verified=False)
    (args.out/'tensor_hashes.json').write_text(json.dumps(dict(expected=expected_hashes,actual=actual_hashes),indent=2),encoding='utf8');(args.out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary),flush=True)
    assert result[1]==0 and result[8]==71 and summary['all_tensor_values_exact'] and summary['mask_exact'],summary
    result.tofile(args.out/'expected_result.bin')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--integer',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--image',type=Path);p.add_argument('--compiled',type=Path);run(p.parse_args())
