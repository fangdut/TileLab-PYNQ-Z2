"""Offline frozen-choice evaluation and independent native HLS-C audit.

Never imported by the operator workstation. Runtime integration must source
the224 rows from the PL preprocessor and combine votes in PL.
"""
from pathlib import Path
import argparse,json,hashlib,subprocess,struct
import numpy as np
from PIL import Image
RUNNER=r'''
#include <ap_int.h>
#include <hls_stream.h>
#include <vector>
#include <fstream>
#include <string>
#include <stdint.h>
void native_line(hls::stream<ap_uint<8>>&,uint64_t*,uint32_t*,unsigned,unsigned,unsigned,unsigned);
int main(int argc,char**argv){if(argc!=8)return 1;std::ifstream f(argv[1],std::ios::binary|std::ios::ate);if(!f)return 2;size_t n=f.tellg();f.seekg(0);std::vector<uint8_t>data(n);f.read((char*)data.data(),n);unsigned w=std::stoul(argv[3]);if(n!=224*w)return 3;hls::stream<ap_uint<8>>input;for(auto v:data)input.write(v);std::vector<uint64_t>stats(3*w);uint32_t result[8];native_line(input,stats.data(),result,w,std::stoul(argv[4]),std::stoul(argv[5]),std::stoul(argv[6]));std::ofstream out(argv[2],std::ios::binary);out.write((char*)result,32);out.write((char*)stats.data(),stats.size()*8);return result[1]?4:0;}
'''
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
    source=Path(__file__).with_name('native_line.cpp');plan=json.loads((a.dataset/'plan.json').read_text(encoding='utf8'))
    manifest=json.loads((a.dataset/'manifest.json').read_text(encoding='utf8'));assert manifest['plan_sha256']==sha(a.dataset/'plan.json')
    thresholds=plan['thresholds'];assert plan['spans']==[2,4,8]
    save(a.out/'execution_plan.json',dict(source_sha256=sha(source),dataset_plan_sha256=sha(a.dataset/'plan.json'),
        initial_source_sha256=plan['source_sha256'],source_change='Explicit int cast resolving ap_int conditional ambiguity only; formula/spans/thresholds fixed before evaluation',
        thresholds=thresholds,scope='OFFLINE_HLS_C_AND_FROZEN_NUMPY_REFERENCE_NOT_BOARD',new_test_files_not_used_for_fit=True))
    (a.out/'kernel.cpp').write_bytes(source.read_bytes());(a.out/'runner.cpp').write_text(RUNNER,encoding='utf8');exe=a.out/'native_check.exe'
    subprocess.run(['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O3','-std=c++17','-static','-Wno-unknown-pragmas','-I','D:/2025.2/Vitis/include',str(a.out/'kernel.cpp'),str(a.out/'runner.cpp'),'-o',str(exe)],check=True)
    results=[]
    for row in manifest['images']:
        file=a.dataset/row['file'];assert sha(file)==row['prepared_sha256'];rgb=np.asarray(Image.open(file).convert('RGB'),dtype=np.int64);height,width=rgb.shape[:2]
        yy=np.clip((2*np.arange(224)+1)*height-224,0,(height-1)*448)//448
        pixels=((rgb[:,:,0]+2*rgb[:,:,1]+rgb[:,:,2])//4)[yy];expected=np.zeros((width,3),dtype='<u8')
        for s,d in enumerate([2,4,8]):
            r=2*pixels[:,d:width-d]-pixels[:,:width-2*d]-pixels[:,2*d:];n=r.sum(0);e=np.abs(r).sum(0)
            alarm=n*n>=(thresholds[s]+1)*(e+1)
            expected[d:width-d,s]=(n&((1<<18)-1)).astype('u8')|(e.astype('u8')<<18)|(alarm.astype('u8')<<35)
        folder=a.out/row['id'];folder.mkdir();pixels.astype('uint8').tofile(folder/'samples.bin');expected.tofile(folder/'expected.bin')
        subprocess.run([str(exe),str(folder/'samples.bin'),str(folder/'actual.bin'),str(width),*[str(t) for t in thresholds],'reserved'],check=True,stdout=subprocess.DEVNULL,timeout=30)
        raw=(folder/'actual.bin').read_bytes();header=struct.unpack_from('<8I',raw);actual=np.frombuffer(raw[32:],dtype='<u8').reshape(width,3)
        if not np.array_equal(actual,expected):raise RuntimeError('Native HLS C N/E/vote differs from independent reference')
        flags=((actual>>35)&1).any(1);assert bool(header[2])==bool(flags.any()) and int(header[3])==int(((actual>>35)&1).sum())
        gt=np.asarray(Image.open(a.dataset/row['mask']).convert('L'))>1;gt_columns=gt.any(0)
        result=dict(id=row['id'],label=row['label'],alarm=int(header[2]),native_vote_columns=np.flatnonzero(flags).tolist(),
            strict_gt_column_hit=bool((flags&gt_columns).any()),all_integer_stats_exact=True,
            source_sha256=sha(source),input_sha256=row['prepared_sha256'])
        results.append(result);save(a.out/'progress.json',results)
    normal=[r for r in results if r['label']=='good'];defect=[r for r in results if r['label']=='defect']
    tp=sum(r['alarm'] for r in defect);fp=sum(r['alarm'] for r in normal)
    summary=dict(scope='FROZEN_CHOICE_NEW_FILE_PILOT_HLS_C_NOT_BOARD_OR_PHYSICAL_TILE_ACCEPTANCE',cases=len(results),tp=tp,fp=fp,tn=len(normal)-fp,fn=len(defect)-tp,
        defect_recall=tp/len(defect),normal_false_positive_rate=fp/len(normal),
        defects_with_strict_gt_column_hit=sum(r['strict_gt_column_hit'] for r in defect),all_integer_stats_exact=True,
        board_verified=False,integrated_with_cnn=False,source_sha256=sha(source),thresholds=thresholds)
    save(a.out/'summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
