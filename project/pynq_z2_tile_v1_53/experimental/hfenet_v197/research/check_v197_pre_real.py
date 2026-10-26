from pathlib import Path
import sys,hashlib,json,zipfile,io,subprocess
import numpy as np
from PIL import Image
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');O=W/'v197_pre_real_c01';O.mkdir(exist_ok=False)
sys.path[:0]=[str(P/'experimental/hfenet_v197'),str(W/'v197_hfe_runtime')];from preprocess_reference import packed_channels
import cv2
(O/'kernel.cpp').write_bytes((P/'experimental/hfenet_v197/preprocess_integer.cpp').read_bytes())
(O/'runner.cpp').write_text(r'''
#include <vector>
#include <fstream>
#include <cstdint>
#include <string>
unsigned preprocess_integer(const uint32_t*,uint32_t*,unsigned,unsigned);
int main(int argc,char**argv){if(argc!=5)return 1;unsigned w=std::stoul(argv[3]),h=std::stoul(argv[4]);std::vector<uint32_t>pixels(w*h),result(w*h);std::ifstream f(argv[1],std::ios::binary);f.read((char*)pixels.data(),pixels.size()*4);if(!f)return 2;if(preprocess_integer(pixels.data(),result.data(),w,h))return 3;std::ofstream out(argv[2],std::ios::binary);out.write((char*)result.data(),result.size()*4);return 0;}
''',encoding='utf8')
subprocess.run(['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O3','-std=c++17','-static','-Wno-unknown-pragmas',str(O/'kernel.cpp'),str(O/'runner.cpp'),'-o',str(O/'check.exe')],check=True)
z=zipfile.ZipFile(W/'v196_hfenet01/HFENet_Dataset.zip');rows=[r for r in json.loads((W/'v196_dataset_hfe01/manifest.json').read_text())['images'] if r['role']=='calibration']+json.loads((W/'v197_new80_01/manifest.json').read_text())['images'];results=[]
for r in rows:
    raw=z.read(r['archive_path']);assert hashlib.sha256(raw).hexdigest()==r['original_sha256'];rgb=np.asarray(Image.open(io.BytesIO(raw)).convert('RGB'));assert np.array_equal(rgb[:,:,0],rgb[:,:,1]) and np.array_equal(rgb[:,:,1],rgb[:,:,2]);gray=rgb[:,:,0];expected=packed_channels(gray);eq=cv2.equalizeHist(gray);summed=cv2.add(gray,eq);author=(gray.astype('u4')<<16)|(eq.astype('u4')<<8)|summed.astype('u4');assert np.array_equal(expected,author)
    packed=(gray.astype('u4')*0x010101).astype('<u4');packed.tofile(O/'scratch_rgb.bin');subprocess.run([str(O/'check.exe'),str(O/'scratch_rgb.bin'),str(O/'scratch_actual.bin'),str(gray.shape[1]),str(gray.shape[0])],check=True)
    actual=np.fromfile(O/'scratch_actual.bin',dtype='<u4').reshape(gray.shape);assert np.array_equal(actual,expected)
    results.append(dict(id=r['id'],shape=list(gray.shape),all_packed_channels_exact=True,source_sha256=r['original_sha256'],actual_sha256=hashlib.sha256(actual.tobytes()).hexdigest(),expected_sha256=hashlib.sha256(expected.tobytes()).hexdigest()))
(O/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8')
summary=dict(scope='AUTHOR_GRAY_INPUT_INTEGER_PREPROCESS_C_AUDIT_NOT_FULL_DETECTOR_RTL_OR_BOARD',images=len(results),all_channels_match_author_opencv_and_integer_oracle=True,all_originals_native256x1408=True,all_source_rgb_channels_equal=True,source_sha256=hashlib.sha256((O/'kernel.cpp').read_bytes()).hexdigest(),raw_pixels_kept_local=True,board_verified=False)
(O/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary))
