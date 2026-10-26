from pathlib import Path
import json,hashlib,subprocess
import numpy as np
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');O=W/'v197_norm_real_c01';O.mkdir(exist_ok=False)
records=json.loads((W/'v197_integer01/first_norm_records_local.json').read_text());params=[];expected=[]
for layer in records:
    for c in layer['channels']:
        n=c['n'];sx=c['input_exp'];eps=c['epsilon'];gamma=None
        # Parameters must come from the actual checkpoint, never infer them from A.
        params.append((layer['node'],c))
import sys,torch,contextlib,io
S=W/'v197_hfenet_source01';sys.path.insert(0,str(S));from hfenet import HFENet
with contextlib.redirect_stdout(io.StringIO()):net=HFENet()
net.load_state_dict(torch.load(S/'checkpoint/model_epoch_69.pth',map_location='cpu',weights_only=True)['model']);net.eval();graph=torch.fx.symbolic_trace(net)
names={node.name:node.target for node in graph.graph.nodes if node.op=='call_module'};wire=[];correct=[];mask=(1<<64)-1
for node,c in params:
    m=graph.get_submodule(names[node]);ch=c['channel'];gamma=int(round(float(m.weight[ch].detach())*2**30));beta=int(round(float(m.bias[ch].detach())*2**30));eps=c['epsilon']
    wire.extend([c['n'],c['sum']&mask,c['sumsq'],eps&mask,eps>>64,gamma&mask,beta&mask,c['output_exp']&mask]);correct.extend([c['root'],c['a']&mask,c['b']&mask,0,c['variance']&mask,c['variance']>>64])
np.asarray(wire,dtype='<u8').tofile(O/'params.bin');np.asarray(correct,dtype='<u8').tofile(O/'expected.bin')
(O/'kernel.cpp').write_bytes((P/'experimental/hfenet_v197/norm_integer.cpp').read_bytes())
(O/'runner.cpp').write_text(r'''
#include <vector>
#include <fstream>
#include <cstdint>
#include <algorithm>
unsigned norm_integer(const uint64_t*,const int16_t*,uint64_t*,int16_t*,unsigned,unsigned);
int main(int argc,char**argv){if(argc!=4)return 1;std::ifstream f(argv[1],std::ios::binary|std::ios::ate);size_t bytes=f.tellg();f.seekg(0);std::vector<uint64_t>p(bytes/8);f.read((char*)p.data(),bytes);size_t count=p.size()/8;if(count*8!=p.size())return 2;std::ofstream out(argv[2],std::ios::binary);std::vector<int16_t>dummy(1,0);for(size_t i=0;i<count;i+=32){unsigned n=std::min(size_t(32),count-i);uint64_t result[192]={};if(norm_integer(p.data()+8*i,dummy.data(),result,dummy.data(),n,0))return 3;out.write((char*)result,n*6*8);}return 0;}
''',encoding='utf8')
subprocess.run(['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O2','-std=c++17','-static','-Wno-unknown-pragmas','-I','D:/2025.2/Vitis/include',str(O/'kernel.cpp'),str(O/'runner.cpp'),'-o',str(O/'check.exe')],check=True)
subprocess.run([str(O/'check.exe'),str(O/'params.bin'),str(O/'actual.bin'),'reserved'],check=True)
assert (O/'actual.bin').read_bytes()==(O/'expected.bin').read_bytes()
summary=dict(scope='REAL_FIRST_INPUT_17_LAYERS_NORMALIZATION_COEFFICIENT_C_AUDIT_NOT_FULL_RTL',channels=len(params),layers=len(records),all_coefficients_variances_roots_exact=True,source_sha256=hashlib.sha256((O/'kernel.cpp').read_bytes()).hexdigest(),actual_sha256=hashlib.sha256((O/'actual.bin').read_bytes()).hexdigest(),expected_sha256=hashlib.sha256((O/'expected.bin').read_bytes()).hexdigest(),raw_feature_moments_kept_local=True,board_verified=False)
(O/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary))
