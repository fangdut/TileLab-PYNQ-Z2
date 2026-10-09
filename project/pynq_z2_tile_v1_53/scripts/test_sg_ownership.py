"""Execute the actual queue + firmware consume/free-slot C with mocked hardware."""
from pathlib import Path
import subprocess, json, hashlib
root=Path(__file__).resolve().parent.parent
out=root/'reports/v137/native_sg';out.mkdir(parents=True,exist_ok=True)
source=root/(root.name+'.sdk')/'ethernet_sources/main.c'
stub='''#ifndef STUB_H
#define STUB_H
#include <stdint.h>
typedef uint64_t XTime;
#define COUNTS_PER_SECOND 325000000ULL
unsigned Xil_In32(unsigned);void Xil_Out32(unsigned,unsigned);
void Xil_DCacheDisable(void);int xil_printf(const char*,...);void XTime_GetTime(XTime*);
#endif
'''
for name in ['xil_io.h','xil_cache.h','xil_printf.h','xiltimer.h']:(out/name).write_text(stub)
(out/'test.c').write_text('''#include <assert.h>
#include <stdio.h>
#define main firmware_main
#include "'''+source.as_posix()+'''"
#undef main
unsigned Xil_In32(unsigned a){return 0;}void Xil_Out32(unsigned a,unsigned b){}
void Xil_DCacheDisable(void){}int xil_printf(const char*f,...){return 0;}
void XTime_GetTime(XTime*t){*t=0;}void tile_network_start(void){}void tile_network_poll(void){}
static uint32_t m[META_WORDS],d[12*40],w[40];
static void init(void){queue_init(&queue,m,d,77);best_slot=-1;dma_used=0;last_seq=0;memset(w,0,sizeof(w));w[0]=0x54465337;w[35]=FRAME_BYTES;}
static void ack(void){m[M_ACK]=queue.head+1;queue_ack(&queue);}
static void crc_consume(unsigned slot,uint32_t *words,XTime now){words[8]=tile_descriptor_crc(words);consume(slot,words,now);}
int main(void){
 unsigned i;init();
 // A material change cannot occur during a live product or first quiet frame.
 threshold=36;m[M_THRESHOLD]=105;m[42]=7;m[43]=1;apply_recipe_if_idle();assert(threshold==36);
 m[43]=0;apply_recipe_if_idle();assert(threshold==36);
 m[43]=4;apply_recipe_if_idle();assert(threshold==105);
 m[M_THRESHOLD]=36;m[42]=0;apply_recipe_if_idle();assert(threshold==36);
 m[M_THRESHOLD]=256;apply_recipe_if_idle();assert(threshold==36);
 init();
 // Physical slot IDs above logical queue length are valid. Shared slot stays pinned.
 w[1]=FRAME_BASE+47*FRAME_STRIDE;assert(queue_publish(&queue,47,w));assert(queue_publish(&queue,47,w));
 assert(queue.refs[47]==2);ack();assert(queue.refs[47]==1 && (queue.slot_used&(1ULL<<47)));ack();assert(!queue.slot_used);
 // Stale and out-of-order acknowledgements cannot free another event.
 assert(queue_publish(&queue,47,w));m[M_ACK]=100;queue_ack(&queue);assert(queue.refs[47]==1 && m[M_ACK_ERRORS]==1);ack();assert(!queue.slot_used);
 init();for(i=0;i<12;i++){w[1]=FRAME_BASE+i*FRAME_STRIDE;assert(queue_publish(&queue,i,w));}assert(!queue_publish(&queue,12,w));
 for(i=0;i<12;i++)ack();assert(!queue.slot_used);
 // A live preview and product-best hold the same frame independently.
 init();m[M_REQUEST]=1;m[M_REASON]=1;w[2]=1;w[37]=1;w[38]=1|2|8|16;crc_consume(40,w,0);
 assert(best_slot==40 && queue.refs[40]==1);ack();assert(best_slot==40 && queue.refs[40]==0);
 dma_used=(1ULL<<40)-1;assert(free_slot()==41);
 // A better frame replaces the old best without overwriting a queued preview.
 m[M_REQUEST]=2;w[2]=2;w[38]=1|8|16;crc_consume(41,w,0);assert(best_slot==41 && queue.refs[41]==1 && free_slot()==40);
 w[2]=3;w[38]=4;crc_consume(42,w,0);assert(best_slot==-1 && m[40]==1 && m[41]==1 && queue.refs[41]==2);
 assert(queue_front(&queue)[37]==1);ack();assert(queue.refs[41]==1);assert(queue_front(&queue)[38]&32);ack();assert(queue.refs[41]==0);
 // Worst legitimate ownership: 32 DMA + 12 queued + one best leaves three free.
 init();dma_used=0xffffffffULL;for(i=32;i<44;i++){w[1]=FRAME_BASE+i*FRAME_STRIDE;assert(queue_publish(&queue,i,w));}best_slot=44;assert(free_slot()==45);
 // Explicit queue-full drop releases best; it must not reclaim any queued frame.
 memset(best,0,sizeof(best));finish_product();assert(best_slot==-1 && m[M_DROPPED]==1 && queue.slot_used==0xfff00000000ULL);
 // Corrupt metadata never updates best, queue, valid counters or product counts.
 init();w[2]=1;w[38]=2|8;w[6]=0x80000000;crc_consume(40,w,0);assert(m[M_INVALID]==1 && !m[M_CAPTURED] && best_slot==-1 && !m[M_DEPTH]);
 puts("PASS actual SG C ownership: shared references, ACK order, 48 slots, best replacement, completed product, overflow and invalid frame");return 0;
}
''')
gcc='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe'
r=subprocess.run([gcc,'-std=c99','-O2','-Wno-int-to-pointer-cast','-I',str(out),str(out/'test.c'),'-o',str(out/'test.exe')],capture_output=True,text=True)
assert r.returncode==0,r.stderr
r=subprocess.run([str(out/'test.exe')],capture_output=True,text=True)
(out/'result.log').write_text(r.stdout+r.stderr)
assert r.returncode==0,r.stdout+r.stderr
(out/'result.json').write_text(json.dumps({'result':'PASS','scope':'actual firmware C, mocked MMIO, not hardware','main_sha256':hashlib.sha256(source.read_bytes()).hexdigest()},indent=2))
print(r.stdout)
