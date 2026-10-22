from pathlib import Path
import json,subprocess,hashlib,shutil,time
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
out=W/'v180_algebra01';out.mkdir(exist_ok=False);source=P/'experimental/winograd_v180/test_exact_transform.cpp';start=time.monotonic()
shutil.copy2(source,out/'test.cpp')
with (out/'compile.log').open('w') as log:
    subprocess.run(['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O3','-std=c++17','-static',str(out/'test.cpp'),'-o',str(out/'test.exe')],stdout=log,stderr=subprocess.STDOUT,check=True)
r=subprocess.run([str(out/'test.exe')],capture_output=True,text=True,check=True);(out/'test.log').write_text(r.stdout+r.stderr)
assert 'EXACT_INTEGER_WINOGRAD_ALGEBRA_PASS cases=100208 basis_coefficients=576' in r.stdout
model=W/'v170_fullint224/graph.json';graph=json.loads(model.read_text());eligible=[]
for i,t in enumerate(graph['tasks'],1):
    if t[0]!=2 or t[11]!=3 or t[12]!=1:continue
    ih,iw,ic,oc=t[7:11];oh=(ih+2*t[13]-t[11])//t[12]+1;ow=(iw+2*t[13]-t[11])//t[12]+1
    assert oh%2==ow%2==0
    storage=((ic+15)//16)*4*iw;assert storage<=2048
    eligible.append(dict(step=i,ih=ih,iw=iw,channels=ic,oh=oh,ow=ow,conservative_four_row_words=storage,direct_scalar_products=oh*ow*oc*9,transformed_scalar_products=oh*ow//4*oc*16))
before=sum(x['direct_scalar_products'] for x in eligible);after=sum(x['transformed_scalar_products'] for x in eligible)
j=dict(scope='EXACT_INTEGER_ALGEBRA_AND_MODEL_GEOMETRY_FEASIBILITY_NOT_HLS_RTL_BOARD_OR_FPS',passed=True,cases=100208,basis_coefficients=576,random_cases=100000,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),model_graph_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),eligible_depthwise_layers=eligible,eligible_product_count_before=before,eligible_product_count_after=after,eligible_product_reduction_fraction=1-after/before,actual_speedup_claimed=False,model_changed=False,threshold_changed=False,board_programmed=False,elapsed_seconds=time.monotonic()-start,paper='https://arxiv.org/abs/1509.09308',interpretation='Both sides are bilinear maps. All144 input/kernel basis pairs verify all576 output coefficients before division. G2=2G yields4*direct convolution exactly. Wide native integers check the identity; explicit bounds are necessary before any finite-width HLS implementation.')
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
