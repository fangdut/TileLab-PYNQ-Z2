from pathlib import Path
import shutil,subprocess,struct,json,hashlib,time
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=W/'v182_decoder_checks01';out.mkdir(exist_ok=False);source=P/'experimental/texture_v170/hls/frozen/v170_hls64.cpp';harness=P/'experimental/control_decode_v182/test_decode.cpp'
shutil.copy2(source,out/'kernel.cpp');shutil.copy2(harness,out/'test.cpp');start=time.monotonic()
with (out/'compile.log').open('w') as log:
    subprocess.run(['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O3','-std=c++17','-static','-Wno-unknown-pragmas','-I','D:/2025.2/Vitis/include',str(out/'test.cpp'),'-o',str(out/'test.exe')],stdout=log,stderr=subprocess.STDOUT,check=True)
r=subprocess.run([str(out/'test.exe')],capture_output=True,text=True,check=True);(out/'test.log').write_text(r.stdout+r.stderr);assert 'RAW32_ONEHOT_DECODE_PASS cases=100268' in r.stdout
raw=(W/'v170_fullint224/model.bin').read_bytes();records=[]
for bad in [0,4,0x10000001,0xffffffff]:
    model=bytearray(raw);struct.pack_into('<I',model,64*4,bad);blob=out/('model_'+str(bad)+'.bin');blob.write_bytes(model);outputs=[]
    for label,folder in [('baseline62','v179_full_c05'),('candidate64','v182_full_c01')]:
        target=out/(label+'_'+str(bad)+'.bin')
        r=subprocess.run([str(W/folder/'check.exe'),str(blob),str(W/'v182_full_c01/input.bin'),str(target),'840','840'],capture_output=True,text=True,timeout=120)
        (out/(label+'_'+str(bad)+'.log')).write_text(r.stdout+r.stderr)
        header=struct.unpack('<16I',target.read_bytes()[:64]);assert r.returncode==2 and header[1]==3,(label,bad,r.returncode,header)
        outputs.append(header)
    assert outputs[0]==outputs[1];records.append(dict(raw_opcode=bad,original_error=3,candidate_error=3,header16_words_identical=True))
j=dict(scope='INDEPENDENT_RAW32_DECODER_C_AND_INVALID_MODEL_PATH_NOT_RTL_OR_BOARD',passed=True,scalar_cases=100268,source_sha256=sha(source),harness_sha256=sha(harness),invalid_models=records,elapsed_seconds=time.monotonic()-start,interpretation='High-bit unsupported opcodes remain rejected; no truncation to supported opcodes. Valid-image C117, RTL and physical timing are separate gates.')
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
