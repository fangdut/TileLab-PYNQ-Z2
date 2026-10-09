"""Actual ARM main.c recipe code with native MMIO stubs, not an FPGA test."""
from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parents[1];S=R/(R.name+'.sdk')/'ethernet_sources'
O=R/'reports/v132/mode_native';O.mkdir(parents=True,exist_ok=True)
stub='''#ifndef STUB_H
#define STUB_H
#include <stdint.h>
typedef uint64_t XTime;
#define COUNTS_PER_SECOND 1000000ULL
unsigned Xil_In32(unsigned);void Xil_Out32(unsigned,unsigned);void Xil_DCacheDisable(void);int xil_printf(const char*,...);void XTime_GetTime(XTime*);
#endif
'''
for name in ('xil_io.h','xil_cache.h','xil_printf.h','xiltimer.h'):(O/name).write_text(stub)
source=r'''
#include <assert.h>
#include <stdio.h>
#define main firmware_main
#include "main.c"
#undef main
static unsigned writes,last_cfg;
unsigned Xil_In32(unsigned a){return 0;}
void Xil_Out32(unsigned a,unsigned b){writes++;if(a==0x41200008u)last_cfg=b;}
void Xil_DCacheDisable(void){}int xil_printf(const char*f,...){return 0;}
void XTime_GetTime(XTime*t){*t=0;}void tile_network_start(void){}void tile_network_poll(void){}
int main(void){
 uint32_t m[META_WORDS],d[12*40];unsigned cases=0;
 queue_init(&queue,m,d,77);
 for(unsigned mode=0;mode<3;mode++)for(unsigned t=1;t<256;t++){
  m[M_DETECT_MODE_REQUEST]=mode;m[M_THRESHOLD]=t;m[42]=9;m[43]=1;
  unsigned prev=writes,old=m[M_CONFIG];apply_recipe_if_idle();
  assert(writes==prev && m[M_CONFIG]==old); // Never change mid-product.
  m[43]=4;apply_recipe_if_idle();
  assert(writes==prev+3 && ((last_cfg>>8)&255)==t && m[M_CONFIG]==last_cfg);
  assert(m[M_DETECT_MODE_APPLIED]==mode);
  assert(((last_cfg>>24)&3)==(mode==0?1:mode==1?0:3));
  assert(((last_cfg^old)>>31)==1); // Each actual commit toggles request bit.
  prev=writes;apply_recipe_if_idle();assert(writes==prev);cases++;
 }
 m[42]=0;m[43]=0;m[M_THRESHOLD]=90;m[M_DETECT_MODE_REQUEST]=2;
 apply_recipe_if_idle();assert(m[M_DETECT_MODE_APPLIED]==2 && threshold==90);
 unsigned prev=writes;
 unsigned invalid_modes[4]={3,4,255,0xffffffffu};
 for(unsigned i=0;i<4;i++){m[M_DETECT_MODE_REQUEST]=invalid_modes[i];m[M_THRESHOLD]=89;apply_recipe_if_idle();assert(writes==prev);cases++;}
 m[M_DETECT_MODE_REQUEST]=0;
 unsigned invalid_t[3]={0,256,0xffffffffu};
 for(unsigned i=0;i<3;i++){m[M_THRESHOLD]=invalid_t[i];apply_recipe_if_idle();assert(writes==prev);cases++;}
 assert(M_WEAK_DISABLE_REQUEST==M_DETECT_MODE_REQUEST && M_WEAK_DISABLE_APPLIED==M_DETECT_MODE_APPLIED);
 printf("PASS %u recipe cases: all thresholds/modes, product-gap commit, duplicate no-op, invalid requests\n",cases);
 return 0;
}
'''
(O/'integration.c').write_text(source)
gcc='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe'
p=subprocess.run([gcc,'-O2','-Wno-int-to-pointer-cast','-I'+str(O),'-I'+str(S),str(O/'integration.c'),'-o',str(O/'integration.exe')],capture_output=True,text=True)
(O/'compile.log').write_text(p.stdout+p.stderr);p.check_returncode()
p=subprocess.run([str(O/'integration.exe')],capture_output=True,text=True);(O/'result.log').write_text(p.stdout+p.stderr);p.check_returncode()
v=dict(passed=True,cases=772,output=p.stdout,main_sha256=hashlib.sha256((S/'main.c').read_bytes()).hexdigest(),scope=__doc__)
(R/'reports/v132/mode_native.json').write_text(json.dumps(v,indent=2));print(p.stdout)
