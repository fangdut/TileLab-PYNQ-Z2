"""Compile real firmware health + integration with controlled time/MMIO."""
from pathlib import Path
import ctypes,subprocess,json,random,hashlib
R=Path(__file__).resolve().parents[1];S=R/(R.name+'.sdk')/'ethernet_sources';O=R/'reports/v137/health_native';O.mkdir(parents=True,exist_ok=True)
gcc='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe'
source=r'''
#include "capture_health.h"
static CaptureHealth h;
__declspec(dllexport) void begin(uint64_t t){health_start(&h,t);}
__declspec(dllexport) void complete(uint64_t t,unsigned good){h.done=t;h.seen_done=1;if(good){h.valid=t;h.seen_valid=1;}}
__declspec(dllexport) void observe(uint64_t t,uint32_t sr,uint32_t cr,uint32_t err,uint32_t *out){health_snapshot(&h,t,333333,out?sr:0,cr,err,out);}
'''
(O/'wrapper.c').write_text(source)
subprocess.run([gcc,'-shared','-O2','-I'+str(S),str(O/'wrapper.c'),'-o',str(O/'health.dll')],check=True,capture_output=True)
lib=ctypes.CDLL(str(O/'health.dll'));lib.begin.argtypes=[ctypes.c_uint64];lib.complete.argtypes=[ctypes.c_uint64,ctypes.c_uint32]
lib.observe.argtypes=[ctypes.c_uint64,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.POINTER(ctypes.c_uint32)]
out=(ctypes.c_uint32*6)();scale=333333
def read(t,sr=0,cr=1,err=0):
 lib.observe(t,sr,cr,err,out);return list(out)
boundaries=[]
def check(name,t,state,sr=0,cr=1,err=0):
 w=read(t,sr,cr,err);assert w[1]==state,(name,w,state);boundaries.append(dict(name=name,words=w))
base=(2**32+5000)*scale
lib.begin(base);check('long startup remains wait',base+20000*scale,0)
lib.complete(base+20001*scale,1);check('first valid',base+20001*scale,1)
check('499ms healthy',base+20500*scale,1);check('500ms stalled',base+20501*scale,2)
lib.complete(base+20501*scale,0);check('DMA continues but valid frame stale',base+20501*scale,3)
lib.complete(base+20502*scale,1);check('valid stream returns',base+20502*scale,1)
check('run bit cleared',base+20502*scale,5,cr=0);check('halt bit set',base+20502*scale,5,sr=1)
for bit in [0x10,0x20,0x40,0x100,0x200,0x400]:check('DMA error '+hex(bit),base+20502*scale,4,sr=bit)
check('slot ownership allocation error',base+20502*scale,4,err=0xbad00001)
lib.begin(base);lib.complete(base+499*scale,0);check('initial malformed grace',base+499*scale,0)
lib.complete(base+500*scale,0);check('persistent malformed startup',base+500*scale,3)
check('age saturation',base+(2**32+20000)*scale,2)
assert read(base+(2**32+20000)*scale)[2:4]==[0xfffffffe,0xffffffff]
# Independent state/time oracle. Never use wrapped frame counters as clocks.
rng=random.Random(119);t=base;lib.begin(t);started=done=valid=t;seen_done=seen_valid=False
for n in range(25000):
 t+=rng.randrange(800)*scale
 if rng.random()<.015:lib.begin(t);started=done=valid=t;seen_done=seen_valid=False
 if rng.random()<.7:
  good=rng.random()<.8;lib.complete(t,good);done=t;seen_done=True
  if good:valid=t;seen_valid=True
 sr=rng.choice([0]*18+[1,0x10,0x400]);cr=rng.choice([1]*19+[0]);err=0xbad00001 if rng.random()<.01 else 0
 da=min((t-done)//scale,0xfffffffe);va=min((t-valid)//scale,0xfffffffe) if seen_valid else 0xffffffff
 if sr&0x770 or err:state=4
 elif not cr&1 or sr&1:state=5
 elif not seen_done:state=0
 elif da>=500:state=2
 elif (not seen_valid and (t-started)//scale>=500) or (seen_valid and va>=500):state=3
 elif not seen_valid:state=0
 else:state=1
 assert read(t,sr,cr,err)==[0x484c5431,state,da,va,sr,cr],n
stub='''#ifndef STUB_H
#define STUB_H
#include <stdint.h>
typedef uint64_t XTime;
#define COUNTS_PER_SECOND 1000000ULL
unsigned Xil_In32(unsigned);void Xil_Out32(unsigned,unsigned);void Xil_DCacheDisable(void);int xil_printf(const char*,...);void XTime_GetTime(XTime*);
#endif
'''
for name in ('xil_io.h','xil_cache.h','xil_printf.h','xiltimer.h'):(O/name).write_text(stub)
integration=r'''
#include <assert.h>
#include <stdio.h>
#define main firmware_main
#include "main.c"
#undef main
static unsigned reads,sr,cr=1;
unsigned Xil_In32(unsigned a){reads++;return a==DMA+0x34?sr:cr;}
void Xil_Out32(unsigned a,unsigned b){}void Xil_DCacheDisable(void){}
int xil_printf(const char*f,...){return 0;}void XTime_GetTime(XTime*t){*t=0;}
void tile_network_start(void){}void tile_network_poll(void){}
int main(void){
 uint32_t m[META_WORDS],d[12*40],w[40]={0};unsigned n;
 queue_init(&queue,m,d,77);health_start(&capture_health,0);
 for(n=0;n<10000;n++)tile_capture_health(n);
 assert(reads==0 && m[M_HEALTH_BASE]==0);
 tile_capture_health(10000);assert(reads==2 && m[66]==TILE_HEALTH_MAGIC && m[67]==0);
 w[0]=0x54465337;w[1]=0xaabbccdd;w[2]=100;w[35]=FRAME_BYTES;w[8]=tile_descriptor_crc(w);
 capture_health.done=11000;capture_health.seen_done=1;consume(40,w,11000);
 tile_capture_health(20000);assert(m[67]==1 && m[68]==9 && m[69]==9 && reads==4);
 tile_capture_health(511000);assert(m[67]==2);
 capture_health.done=520000;w[8]^=1;consume(41,w,520000);
 tile_capture_health(521000);assert(m[67]==3 && m[M_CAPTURED]==1);
 m[M_ERRORS]=0xbad00001;tile_capture_health(531000);assert(m[67]==4 && dma_recovery.attempts==0);
 assert(m[M_CAPTURED]==1 && queue.head==0 && queue.tail==0);
 puts("PASS actual main.c: 10000 fast-path calls no MMIO, 100Hz snapshot, valid/malformed consume timestamps and software-error precedence (DMA auto-recovery has a separate test)");return 0;
}
'''
(O/'integration.c').write_text(integration)
p=subprocess.run([gcc,'-O2','-Wno-int-to-pointer-cast','-I'+str(O),'-I'+str(S),str(O/'integration.c'),'-o',str(O/'integration.exe')],capture_output=True,text=True)
(O/'compile.log').write_text(p.stdout+p.stderr);p.check_returncode()
p=subprocess.run([str(O/'integration.exe')],capture_output=True,text=True);(O/'integration.log').write_text(p.stdout+p.stderr);p.check_returncode()
result=dict(passed=True,boundaries=boundaries,random_operations=25000,actual_main_integration=p.stdout,health_header_sha256=hashlib.sha256((S/'capture_health.h').read_bytes()).hexdigest(),main_sha256=hashlib.sha256((S/'main.c').read_bytes()).hexdigest(),scope='Compiled actual C with simulated time/MMIO; hardware tests are recorded separately')
(R/'reports/v137/health_native.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(passed=True,boundary_cases=len(boundaries),random_operations=25000,integration=p.stdout)))
