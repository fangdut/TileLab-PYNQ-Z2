"""Actual C descriptor CRC and consume() rejection; native mocked MMIO."""
from pathlib import Path
import subprocess,ctypes,random,struct,zlib,json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v137/descriptor_native';O.mkdir(parents=True,exist_ok=True)
S=R/(R.name+'.sdk')/'ethernet_sources'
gcc='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe'
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
unsigned Xil_In32(unsigned a){return 0;}void Xil_Out32(unsigned a,unsigned b){}
void Xil_DCacheDisable(void){}int xil_printf(const char*f,...){return 0;}
void XTime_GetTime(XTime*t){*t=0;}void tile_network_start(void){}void tile_network_poll(void){}
static uint32_t m[META_WORDS],d[12*40];
int main(void){
 uint32_t good[40]={0},damaged[40];unsigned word,bit;
 queue_init(&queue,m,d,77);best_slot=-1;
 good[0]=0x54465337;good[1]=0xaabbccdd;good[2]=100;good[6]=4;good[35]=FRAME_BYTES;
 good[37]=12;good[38]=1|2|8|16;good[8]=tile_descriptor_crc(good);
 consume(40,good,999);assert(m[M_CAPTURED]==1 && m[M_DESC_VERIFIED]==1 && best_slot==40);
 assert(m[M_LAST_DESC_CRC]==good[8] && tile_slot_crc[40]==good[1]);
 for(word=0;word<40;word++)for(bit=0;bit<32;bit++){
  memcpy(damaged,good,sizeof(good));damaged[word]^=1u<<bit;
  consume(41,damaged,1000);
  assert(m[M_CAPTURED]==1 && m[M_DESC_VERIFIED]==1 && best_slot==40);
  assert(tile_slot_crc[41]==0 && queue.tail==0 && m[42]==12 && last_seq==100);
 }
 assert(m[M_INVALID]==1280 && m[M_DESC_CRC_ERRORS]==1248);
 /* Invalid video with a valid descriptor CRC is still rejected separately. */
 memcpy(damaged,good,sizeof(good));damaged[6]|=0x80000000;damaged[8]=tile_descriptor_crc(damaged);
 consume(41,damaged,1001);assert(m[M_INVALID]==1281 && m[M_DESC_CRC_ERRORS]==1248 && best_slot==40);
 /* Even a valid CRC cannot upgrade an old hardware format. */
 memcpy(damaged,good,sizeof(good));damaged[0]=0x54465336;damaged[8]=tile_descriptor_crc(damaged);
 consume(41,damaged,1002);assert(m[M_INVALID]==1282 && best_slot==40);
 /* Good successor still carries its own pixel CRC and can replace best. */
 memcpy(damaged,good,sizeof(good));damaged[1]=0x12345678;damaged[2]=101;damaged[38]=1|8|16;damaged[8]=tile_descriptor_crc(damaged);
 consume(41,damaged,1003);assert(m[M_CAPTURED]==2 && m[M_DESC_VERIFIED]==2 && best_slot==41);
 assert(tile_slot_crc[41]==0x12345678 && best[8]==0);
 puts("PASS actual main.c: 1280 single-bit descriptor corruptions rejected before decisions; bad-video and old magic rejected; valid successor accepted");return 0;
}
'''
(O/'test.c').write_text(source)
p=subprocess.run([gcc,'-std=c11','-O2','-Wno-int-to-pointer-cast','-I'+str(O),'-I'+str(S),str(O/'test.c'),'-o',str(O/'test.exe')],capture_output=True,text=True)
(O/'compile.log').write_text(p.stdout+p.stderr);p.check_returncode()
p=subprocess.run([str(O/'test.exe')],capture_output=True,text=True);(O/'test.log').write_text(p.stdout+p.stderr);p.check_returncode()
(O/'wrapper.c').write_text('#include "descriptor_crc.h"\n__declspec(dllexport) uint32_t crc(const uint32_t *p){return tile_descriptor_crc(p);}\n')
subprocess.run([gcc,'-shared','-O2','-I'+str(S),str(O/'wrapper.c'),'-o',str(O/'crc.dll')],check=True,capture_output=True)
lib=ctypes.CDLL(str(O/'crc.dll'));lib.crc.argtypes=[ctypes.POINTER(ctypes.c_uint32)];lib.crc.restype=ctypes.c_uint32
rand=random.Random(114);cases=3000
for i in range(cases):
    words=[rand.getrandbits(32) for _ in range(40)];actual=lib.crc((ctypes.c_uint32*40)(*words));words[8]=0
    assert actual==zlib.crc32(struct.pack('<40I',*words)),i
result=dict(passed=True,random_crc_cases=cases,single_bit_corruptions=1280,descriptor_crc_errors=1248,scope='Actual C CRC and actual main.c with mocked MMIO, not DMA/ARM timing or physical fault injection',main_sha256=hashlib.sha256((S/'main.c').read_bytes()).hexdigest(),crc_sha256=hashlib.sha256((S/'descriptor_crc.h').read_bytes()).hexdigest(),output=p.stdout)
(R/'reports/v137/descriptor_native.json').write_text(json.dumps(result,indent=2));print(p.stdout);print('PASS 3000 CRCs against independent zlib')
