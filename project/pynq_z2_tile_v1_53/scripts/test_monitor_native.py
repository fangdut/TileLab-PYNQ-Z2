from pathlib import Path
import subprocess,json,hashlib
p=Path(__file__).resolve().parent.parent;r=p/'reports/native_monitor';r.mkdir(exist_ok=True)
stub='''#include <stdint.h>
#include <stdarg.h>
typedef uint64_t XTime;
#define COUNTS_PER_SECOND (650000000 / 2)
#define XUARTPS_FIFO_OFFSET 0
unsigned Xil_In32(unsigned);void Xil_Out32(unsigned,unsigned);int xil_printf(const char*,...);
int XUartPs_IsReceiveData(unsigned);unsigned XUartPs_ReadReg(unsigned,unsigned);
void XTime_GetTime(XTime*);void usleep(unsigned);
'''
for name in ['xil_io.h','xil_printf.h','xuartps_hw.h','xiltimer.h','sleep.h']:(r/name).write_text(stub)
source=p/(p.name+'.sdk')/'app_sources/main.c'
(r/'test.c').write_text('''#include <assert.h>
#define main firmware_main
#include "'''+source.as_posix()+'''"
#undef main
static unsigned writes=0,lastword=0,seq=1;
unsigned Xil_In32(unsigned a){
 if(a==BRIGHT1)return seq;
 if(a==BRIGHT0)return 100;
 if(a==BRIGHT0+8)return 20000;
 if(a==BRIGHT1+8)return current_word;
 if(a==BRIGHT2)return (y0<<16)|x0;
 if(a==BRIGHT2+8)return (y1<<16)|x1;
 return 0;
}
void Xil_Out32(unsigned a,unsigned b){writes++;if(a==FRAME_BASE+8)lastword=b;}
int xil_printf(const char*f,...){return 0;}
int XUartPs_IsReceiveData(unsigned a){return 0;}
unsigned XUartPs_ReadReg(unsigned a,unsigned b){return 0;}
void XTime_GetTime(XTime*a){*a=0;}
void usleep(unsigned a){}
int main(void){
 apply();assert(source==3 && threshold==36 && mode==7 && roi==1);assert(lastword&(1u<<22));assert(lastword&(1u<<23));
 command("v 0");assert(!(lastword&(1u<<23)));command("v 1");assert(lastword&(1u<<23));
 command("e 0");assert(!(lastword&(1u<<22)));command("e 1");assert(lastword&(1u<<22));
 command("s 3");assert(((lastword>>16)&3)==3);command("t 24");assert(((lastword>>8)&255)==24);
 unsigned old=writes;command("a 1");assert(automatic_enabled==0 && writes==old);
 command("s 4");command("e 2");command("q -1");command("e 1 garbage");command("r 9 0 8 2");assert(writes==old);
 command("r 0 0 1279 719");assert(x0==0 && y0==0 && x1==1279 && y1==719);
 command("q 0");assert(!(lastword&(1u<<21)));command("q 1");assert(lastword&(1u<<21));
 command("m 0");assert((lastword&7)==0);command("m 7");assert((lastword&7)==7);
 puts("PASS native monitor: Tile defaults, PL contrast source, thin-line bypass, manual margin, CPU auto disabled, invalid commands and ROI");return 0;
}
''')
gcc=Path('D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe')
q=subprocess.run([str(gcc),'-std=c99','-O2','-I',str(r),str(r/'test.c'),'-o',str(r/'test.exe')],capture_output=True,text=True);assert q.returncode==0,q.stderr
q=subprocess.run([str(r/'test.exe')],capture_output=True,text=True);(r/'result.log').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr
(p/'reports/native_monitor.json').write_text(json.dumps({'result':'PASS','scope':'actual monitor C with mocked registers; no hardware','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()},indent=2));print(q.stdout)

