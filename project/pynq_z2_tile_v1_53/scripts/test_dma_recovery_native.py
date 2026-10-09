"""Compile actual firmware with controlled MMIO/time and mapped BD memory.
This is a native state/ownership test, not a simulated FPGA or DMA bus.
"""
from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parents[1];S=R/(R.name+'.sdk')/'ethernet_sources';O=R/'reports/v137/recovery_native';O.mkdir(parents=True,exist_ok=True)
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
#include <windows.h>
#include <assert.h>
#include <stdio.h>
#define main firmware_main
#include "main.c"
#undef main
static uint32_t m[META_WORDS],d[12*40],saved_d[12*40],saved_crc[48];
static unsigned cr,sr,cap,reset_requests,starts;static XTime clock_now;
unsigned Xil_In32(unsigned a){return a==DMA+0x30?cr:a==DMA+0x34?sr:1234;}
void Xil_Out32(unsigned a,unsigned b){
 if(a==DMA+0x30){cr=b;if(b&4){reset_requests++;sr=1;}else if(b&1){starts++;sr=0;}else sr|=1;}
 if(a==CAP0+8)cap=b;
}
void Xil_DCacheDisable(void){}int xil_printf(const char*f,...){return 0;}
void XTime_GetTime(XTime*t){*t=clock_now;}void tile_network_start(void){}void tile_network_poll(void){}
static void poll(unsigned ms){clock_now=(uint64_t)ms*1000;tile_capture_health(clock_now);}
static void init(unsigned pin){
 unsigned i,slots[12]={0,2,2,8,10,12,14,16,18,20,22,24};uint32_t w[40]={0};
 memset(&dma_recovery,0,sizeof(dma_recovery));queue_init(&queue,m,d,77);
 best_slot=-1;dma_used=0;last_seq=0;cap=2;cr=1;sr=0;reset_requests=starts=0;clock_now=0;
 health_start(&capture_health,0);capture_health.seen_done=capture_health.seen_valid=1;
 for(i=0;i<48;i++)tile_slot_crc[i]=0xaabb0000+i;
 if(pin){for(i=0;i<12;i++){w[1]=FRAME_BASE+slots[i]*FRAME_STRIDE;w[2]=100+i;assert(queue_publish(&queue,slots[i],w));}best_slot=2;m[42]=7;}
 memcpy(saved_d,d,sizeof(d));memcpy(saved_crc,tile_slot_crc,sizeof(saved_crc));
 assert(ring_populate());
}
static void preserved(void){
 assert(queue.head==0 && queue.tail==12 && m[M_DEPTH]==12 && queue.refs[2]==2);
 assert(!memcmp(saved_d,d,sizeof(d)));
 for(unsigned i=0;i<48;i++)if(queue.refs[i])assert(saved_crc[i]==tile_slot_crc[i]);
}
static void check_ring(void){
 uint64_t used=0;
 for(unsigned i=0;i<32;i++){
  volatile uint32_t *bd=(volatile uint32_t*)(BD_BASE+i*64);
  unsigned slot=(bd[2]-FRAME_BASE)/FRAME_STRIDE;
  assert(slot<48 && !(queue.slot_used&(1ULL<<slot)) && !(used&(1ULL<<slot)));
  assert(bd[0]==BD_BASE+((i+1)%32)*64 && bd[6]==PACKET_BYTES && bd[7]==0);
  used|=1ULL<<slot;
 }
 assert(used==dma_used);
}
static void frame(unsigned seq,unsigned flags,unsigned corrupt,unsigned ms){
 uint32_t w[40]={0};clock_now=(uint64_t)ms*1000;
 w[0]=0x54465337;w[1]=0xcafe1234;w[2]=seq;w[35]=FRAME_BYTES;w[37]=8;w[38]=flags;w[8]=tile_descriptor_crc(w);
 if(corrupt)w[8]^=1;
 capture_health.done=clock_now;capture_health.seen_done=1;
 consume(45,w,clock_now);
}
static void fault(unsigned ms,unsigned status){sr=status;cr=0;poll(ms);assert(dma_recovery.state==REC_RESETTING && cap==0 && cr==4 && m[67]==6);}
static void reset_done(unsigned ms){cr=0;sr=1;poll(ms);assert(dma_recovery.state==REC_VERIFYING && cr==1 && cap==2);check_ring();}
int main(void){
 unsigned i,base,scenarios=0;
 assert(VirtualAlloc((void*)BD_BASE,65536,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE)==(void*)BD_BASE);
 // 12 logical events, a shared low physical slot and best sharing that slot.
 init(1);fault(10,1);preserved();assert(best_slot==-1 && dma_recovery.interrupted==1);
 reset_done(20);preserved();frame(1,1|8|16,0,30);poll(30);assert(dma_recovery.state==REC_VERIFYING && best_slot==-1);
 frame(2,1|8|16,1,40);poll(40);assert(dma_recovery.good==0 && dma_recovery.discarded==1);
 frame(3,1|8|16,0,50);poll(50);assert(dma_recovery.state==REC_VERIFYING);
 frame(4,1|8|16,0,60);poll(60);assert(dma_recovery.state==REC_RUNNING && dma_recovery.successes==1 && m[M_ERRORS]==0);preserved();
 // Mid-product / EXIT alone cannot publish a stale best frame.
 frame(5,1|8|16,0,70);frame(6,4,0,80);assert(best_slot==-1 && m[40]==0 && queue.tail==12);
 frame(7,1|2|8|16,0,90);assert(best_slot==45 && !dma_recovery.wait_product && best[8]==256);preserved();scenarios++;
 // Across all explicit DMA error bits, recovery reuses no pinned slot.
 for(i=0;i<6;i++){
  unsigned bits[6]={0x10,0x20,0x40,0x100,0x200,0x400};init(1);fault(10,bits[i]);reset_done(20);
  frame(1,0,0,30);frame(2,0,0,40);poll(40);assert(dma_recovery.successes==1);preserved();scenarios++;
 }
 // Exactly bounded reset timeout; never reissue reset while it is stuck high.
 init(1);fault(10,1);poll(1000);assert(dma_recovery.state==REC_RESETTING);
 poll(1010);assert(dma_recovery.state==REC_FAILED && dma_recovery.reason==REC_REASON_RESET_TIMEOUT && reset_requests==1 && cap==0);preserved();
 poll(10000);assert(reset_requests==1 && dma_recovery.failures==1 && m[M_FRAMES]==1234);scenarios++;
 // No complete image after rearm, including persistent malformed packets.
 init(1);fault(10,1);reset_done(20);
 for(i=30;i<3020;i+=10){frame(i,0,1,i);poll(i);assert(dma_recovery.state==REC_VERIFYING);}
 poll(3020);assert(dma_recovery.state==REC_FAILED && dma_recovery.reason==REC_REASON_VERIFY_TIMEOUT && !(cr&1));preserved();scenarios++;
 // Validity is timed at consume, not the later 10ms status poll boundary.
 init(1);fault(10,1);reset_done(20);frame(1,0,0,3000);frame(2,0,0,3019);poll(3020);
 assert(dma_recovery.state==REC_RUNNING && dma_recovery.successes==1);preserved();scenarios++;
 init(1);fault(10,1);reset_done(20);frame(1,0,0,3000);frame(2,0,0,3020);poll(3020);
 assert(dma_recovery.state==REC_FAILED && dma_recovery.reason==REC_REASON_VERIFY_TIMEOUT);preserved();scenarios++;
 // A second DMA error during verification fails rather than recursively resetting.
 init(1);fault(10,1);reset_done(20);sr=0x40;cr=0;poll(30);
 assert(dma_recovery.state==REC_FAILED && dma_recovery.reason==REC_REASON_REPEAT_DMA_ERROR && reset_requests==1);preserved();scenarios++;
 // Three independent successful attempts, then a fourth stop is latched.
 init(1);
 for(i=0;i<3;i++){base=10+i*100;fault(base,1);reset_done(base+10);frame(i*2+1,0,0,base+20);frame(i*2+2,0,0,base+30);poll(base+30);assert(dma_recovery.successes==i+1);preserved();}
 cr=0;sr=1;poll(400);assert(dma_recovery.state==REC_FAILED && dma_recovery.reason==REC_REASON_BUDGET && dma_recovery.attempts==3 && reset_requests==3);preserved();scenarios++;
 // Startup waiting and a pure no-progress/input-gate pause never cause resets.
 init(0);capture_health.seen_done=capture_health.seen_valid=0;poll(10000);assert(reset_requests==0 && m[67]==0);
 capture_health.seen_done=capture_health.seen_valid=1;poll(20000);assert(reset_requests==0 && m[67]==2);scenarios++;
 // No free-slot failure can overwrite held queue addresses.
 init(1);fault(10,1);queue.slot_used=(1ULL<<48)-1;cr=0;sr=1;poll(20);
 assert(dma_recovery.state==REC_FAILED && dma_recovery.reason==REC_REASON_NO_SLOTS && cap==0);assert(!memcmp(saved_d,d,sizeof(d)));scenarios++;
 // Terminal failure does not prevent acknowledging original retained evidence.
 m[M_ACK]=1;queue_ack(&queue);assert(queue.head==1 && queue.tail==12 && queue.refs[0]==0);scenarios++;
 // Frame-bound identity is preserved at delayed product publication.
 for(i=0;i<4;i++){
  init(0);dma_recovery.successes=i;frame(100,1|2|8|16,0,1);
  assert(best[8]==(i<<8));dma_recovery.successes=3;finish_product();
  assert(queue_front(&queue)[8]==((i<<8)|1));
  m[M_ACK]=1;queue_ack(&queue);
  dma_recovery.successes=i;m[M_REQUEST]=1;m[M_REASON]=2;frame(101,0,0,2);
  assert(queue_front(&queue)[8]==((i<<8)|3));m[M_ACK]=2;queue_ack(&queue);
  m[M_REQUEST]=2;m[M_REASON]=1;frame(102,0,0,3);
  assert(queue_front(&queue)[8]==((i<<8)|2));scenarios++;
 }
 assert(VirtualFree((void*)BD_BASE,0,MEM_RELEASE));
 printf("PASS %u actual-main scenarios: bounded reset/verify, all DMA error bits, 12 retained events/shared slots, start-gated products, 3-attempt limit and ACK after failure\n",scenarios);return 0;
}
'''
(O/'test.c').write_text(source)
p=subprocess.run([gcc,'-std=c11','-O2','-Wno-int-to-pointer-cast','-I'+str(O),'-I'+str(S),str(O/'test.c'),'-o',str(O/'test.exe')],capture_output=True,text=True)
(O/'compile.log').write_text(p.stdout+p.stderr);p.check_returncode()
p=subprocess.run([str(O/'test.exe')],capture_output=True,text=True);(O/'result.log').write_text(p.stdout+p.stderr);p.check_returncode()
result=dict(passed=True,scenarios=20,output=p.stdout,main_sha256=hashlib.sha256((S/'main.c').read_bytes()).hexdigest(),recovery_header_sha256=hashlib.sha256((S/'dma_recovery.h').read_bytes()).hexdigest(),identity_header_sha256=hashlib.sha256((S/'event_identity.h').read_bytes()).hexdigest(),scope='Actual compiled firmware, mocked MMIO/time and real mapped BD memory; does not emulate physical AXIS/DMA writes or video-clock loss')
(R/'reports/v137/dma_recovery_native.json').write_text(json.dumps(result,indent=2));print(p.stdout)
