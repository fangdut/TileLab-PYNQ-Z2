"""Compile the actual firmware acquisition code with I/O stubs, no board writes."""
from pathlib import Path
import subprocess,json
R=Path(__file__).resolve().parents[1];O=R/'reports/v137/firmware_crc_native';O.mkdir(parents=True,exist_ok=True)
headers={
 'xil_io.h':'#include <stdint.h>\nstatic inline void Xil_Out32(uint32_t a,uint32_t v){(void)a;(void)v;}\nstatic inline uint32_t Xil_In32(uint32_t a){(void)a;return 0;}\n',
 'xil_cache.h':'static inline void Xil_DCacheDisable(void){}\n',
 'xil_printf.h':'static inline int xil_printf(const char *f,...){(void)f;return 0;}\n',
 'xiltimer.h':'#include <stdint.h>\ntypedef uint64_t XTime;\n#define COUNTS_PER_SECOND 1000000ULL\nstatic inline void XTime_GetTime(XTime *t){static XTime n=0;*t=++n;}\n'}
for name,s in headers.items():(O/name).write_text(s)
source=r'''
#include <assert.h>
#include <stdio.h>
#define main firmware_main
#include "main.c"
#undef main
void tile_network_start(void){}
void tile_network_poll(void){}
static uint32_t meta_mem[META_WORDS],desc_mem[QUEUE_CAPACITY*DESC_WORDS];
static void input(unsigned slot,uint32_t crc,uint32_t seq,uint32_t flags,uint32_t magic){
 uint32_t w[DESC_WORDS]={0};w[0]=magic;w[1]=crc;w[2]=seq;
 w[6]=4;w[35]=FRAME_BYTES;w[37]=7;w[38]=flags;
 w[8]=tile_descriptor_crc(w);consume(slot,w,987654000ULL);
}
int main(void){
 queue_init(&queue,meta_mem,desc_mem,1234);
 input(2,0x11112222,1,8,0x54465337);
 assert(best_slot==2 && best[1]==FRAME_BASE+2*FRAME_STRIDE);
 assert(tile_slot_crc[2]==0x11112222 && queue.tail==0);
 input(3,0x33334444,2,8,0x54465337);
 assert(best_slot==3 && tile_slot_crc[3]==0x33334444);
 input(4,0x55556666,3,4,0x54465337);
 assert(best_slot==-1 && queue.tail==1 && queue.refs[3]==1);
 assert(desc_mem[1]==FRAME_BASE+3*FRAME_STRIDE);
 assert(tile_slot_crc[3]==0x33334444);
 /* Queue and best-frame can refer to the same slot independently. */
 meta_mem[M_REQUEST]=1;meta_mem[M_REASON]=2;
 input(5,0x77778888,4,8,0x54465337);
 assert(best_slot==5 && queue.refs[5]==1 && queue.tail==2);
 assert(desc_mem[DESC_WORDS+1]==FRAME_BASE+5*FRAME_STRIDE);
 assert(meta_mem[M_REQUEST_ACK]==1 && tile_slot_crc[5]==0x77778888);
 meta_mem[M_ACK]=1;queue_ack(&queue);
 assert(queue.refs[3]==0 && queue.head==1 && best_slot==5);
 meta_mem[M_ACK]=2;queue_ack(&queue);
 assert(queue.refs[5]==0 && best_slot==5);
 dma_used=((1ULL<<FRAME_SLOTS)-1)&~(1ULL<<5)&~(1ULL<<6);
 assert(free_slot()==6); /* best reference excludes slot 5 after preview ACK */
 input(6,0x9999aaaa,5,4,0x54465337);
 assert(queue.refs[5]==1 && queue.tail==3 && tile_slot_crc[5]==0x77778888);
 assert(desc_mem[2*DESC_WORDS+1]==FRAME_BASE+5*FRAME_STRIDE);
 unsigned captured=meta_mem[M_CAPTURED],invalid=meta_mem[M_INVALID];
 input(7,0,6,0,0x54465334);
 assert(meta_mem[M_INVALID]==invalid+1 && meta_mem[M_CAPTURED]==captured);
 assert(tile_slot_crc[7]==0); /* old hardware rejected, no fabricated CRC */
 printf("PASS actual firmware CRC slot ownership, best replacement, queue references, preview ACK, old magic rejection\n");
 return 0;
}
'''
(O/'test.c').write_text(source)
gcc=Path('D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe')
cmd=[str(gcc),'-std=c11','-O2','-I'+str(O),'-I'+str(R/'pynq_z2_tile_v1_53.sdk/ethernet_sources'),str(O/'test.c'),'-o',str(O/'test.exe')]
r=subprocess.run(cmd,capture_output=True,text=True);(O/'compile.log').write_text(r.stdout+r.stderr);r.check_returncode()
r=subprocess.run([str(O/'test.exe')],capture_output=True,text=True);(O/'test.log').write_text(r.stdout+r.stderr);r.check_returncode()
(R/'reports/v137/firmware_crc_test.json').write_text(json.dumps(dict(passed=True,scope='Actual main.c with mocked hardware I/O; native host pointers do not exercise DMA or ARM cache',output=r.stdout),indent=2))
print(r.stdout)
