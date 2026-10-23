"""Exhaust legal resize geometry and actual bounded HLS row-offset helper.

This native check is offline evidence, not a hardware performance measurement.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,time

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    source=Path(__file__).with_name('texture_row_address.cpp');a.out.mkdir(parents=True,exist_ok=False)
    text=source.read_text()
    guard='if(h[0]!=0x17000001||!width||!height||width>1024||height>1024||side<8||side>224'
    assert guard in text and text.index(guard)<text.index('row0_offset=row_offset')
    cpp='''#include <cstdio>
#include "'''+source.as_posix()+'''"
int main(){
 unsigned long long geometries=0,offsets=0;unsigned max_row=0,max_offset=0;
 for(int side=8;side<=224;side++)for(int height=1;height<=1024;height++)for(int y=0;y<side;y++){
  // Original signed-int expression, with no ap_int narrowing.
  int den=side*2, yy=(2*y+1)*height-side, upper=(height-1)*den;
  if(yy<0)yy=0;if(yy>upper)yy=upper;
  int y0=yy/den,y1=y0+1<height?y0+1:y0;
  if(y0<0||y1<0||y0>=height||y1>=height||y0>1023||y1>1023)return 2;
  if(unsigned(y1)>max_row)max_row=y1;
  geometries++;
 }
 for(unsigned row=0;row<1024;row++)for(unsigned width=1;width<=1024;width++){
  unsigned expected=row*width,actual=row_offset(ap_uint<10>(row),ap_uint<11>(width));
  if(expected!=actual||expected>=1u<<21)return 3;
  if(actual>max_offset)max_offset=actual;
  offsets++;
 }
 printf("{\\"geometry_cases\\":%llu,\\"offset_cases\\":%llu,\\"max_row\\":%u,\\"max_offset\\":%u}\\n",geometries,offsets,max_row,max_offset);
 return 0;
}
'''
    (a.out/'check.cpp').write_text(cpp);exe=a.out/'check.exe';started=time.monotonic()
    subprocess.run(['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O3','-std=c++17','-static','-Wno-unknown-pragmas','-I','D:/2025.2/Vitis/include',str(a.out/'check.cpp'),'-o',str(exe)],check=True,timeout=300)
    result=subprocess.run([str(exe)],capture_output=True,text=True,check=True,timeout=120)
    values=json.loads(result.stdout);assert values['offset_cases']==1048576 and values['geometry_cases']==25776128 and values['max_row']<=1023 and values['max_offset']==1047552
    j=dict(scope='EXHAUSTIVE_GEOMETRY_AND_NATIVE_HLS_HELPER_NOT_RTL_OR_BOARD',passed=True,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),original_invalid_input_guard_retained=True,
        **values,elapsed_seconds=time.monotonic()-started)
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
if __name__=='__main__':main()
