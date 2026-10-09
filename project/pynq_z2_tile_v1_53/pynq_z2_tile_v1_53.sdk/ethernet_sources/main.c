/* V1.52: ARM transports PL decisions; optional wide weak support is set by
 * one PL configuration bit at a physical product gap, never computed by ARM.
 * SG ring has 32 pre-posted descriptors and 48 individually owned DDR slots.
 * Queue, current best frame and DMA each hold independent ownership references.
 */
#include <string.h>
#include "xil_io.h"
#include "xil_cache.h"
#include "xil_printf.h"
#include "xiltimer.h"
#include "event_queue.h"
#include "network.h"
#include "descriptor_crc.h"
#include "capture_health.h"
#include "dma_recovery.h"
#include "event_identity.h"
#define DMA 0x40400000u
#define CAP0 0x41290000u
#define BD_BASE 0x10010000u
#define BD_COUNT 32u
#define PACKET_BYTES (FRAME_BYTES+DESC_WORDS*4u)
EventQueue queue;
/* Owned by the same slot references as pixels; never recomputed by ARM. */
uint32_t tile_slot_crc[FRAME_SLOTS];
static unsigned threshold=0,commit=0,cursor=0,last_seq=0;
static uint64_t dma_used=0;
static int best_slot=-1;
static uint32_t best[DESC_WORDS];
static CaptureHealth capture_health;
static TileDmaRecovery dma_recovery;
void tile_capture_health(uint64_t now);
static void config(unsigned t){
 commit^=0x80000000u;threshold=t;
 Xil_Out32(0x41210000u,0x00500050u);Xil_Out32(0x41210008u,0x027f04afu);
 queue.meta[M_DETECT_MODE_APPLIED]=(queue.meta[M_DETECT_MODE_REQUEST]<=2u)?queue.meta[M_DETECT_MODE_REQUEST]:0u;
 queue.meta[M_PRODUCT_GATE_APPLIED]=queue.meta[M_PRODUCT_GATE_REQUEST]==1u;
 queue.meta[M_WIDE_WEAK_APPLIED]=queue.meta[M_WIDE_WEAK_REQUEST]==1u && queue.meta[M_DETECT_MODE_APPLIED]==2u;
 queue.meta[M_CONFIG]=commit|0x00f30007u|(queue.meta[M_DETECT_MODE_APPLIED]==1u?0:0x01000000u)|
  (queue.meta[M_DETECT_MODE_APPLIED]==2u?0x02000000u:0u)|(queue.meta[M_PRODUCT_GATE_APPLIED]?0x04000000u:0u)|
  (queue.meta[M_WIDE_WEAK_APPLIED]?0x08000000u:0u)|(t<<8);
 Xil_Out32(0x41200008u,queue.meta[M_CONFIG]);
}
static unsigned free_slot(void){
 unsigned i;uint64_t used=dma_used|queue.slot_used|(best_slot>=0?(1ULL<<best_slot):0);
 for(i=0;i<FRAME_SLOTS;i++)if(!(used&(1ULL<<i)))return i;
 return FRAME_SLOTS;
}
static unsigned reset_dma(void){
 XTime t,now;XTime_GetTime(&t);Xil_Out32(DMA+0x30,4);
 do{XTime_GetTime(&now);if(now-t>COUNTS_PER_SECOND)return 0;}while(Xil_In32(DMA+0x30)&4);
 return 1;
}
static unsigned ring_populate(void){
 unsigned n,i,s;volatile uint32_t *bd;
 dma_used=0;cursor=0;
 for(n=0;n<BD_COUNT;n++){
  bd=(volatile uint32_t*)(BD_BASE+n*64);s=free_slot();if(s>=FRAME_SLOTS)return 0;dma_used|=1ULL<<s;
  for(i=0;i<16;i++)bd[i]=0;
  bd[0]=BD_BASE+((n+1)%BD_COUNT)*64;bd[2]=FRAME_BASE+s*FRAME_STRIDE;bd[6]=PACKET_BYTES;
 }
 queue_barrier();Xil_Out32(DMA+0x38,BD_BASE);Xil_Out32(DMA+0x3c,0);
 Xil_Out32(DMA+0x34,0x7000);Xil_Out32(DMA+0x30,1);
 Xil_Out32(DMA+0x44,0);Xil_Out32(DMA+0x40,BD_BASE+(BD_COUNT-1)*64);
 return 1;
}
static unsigned ring_start(void){
 if(!reset_dma() || !ring_populate())return 0;
 Xil_Out32(CAP0+8,2);queue.meta[M_ACTIVE]=1;XTime health_now;XTime_GetTime(&health_now);health_start(&capture_health,health_now);capture_health.published=health_now-10ULL*(COUNTS_PER_SECOND/1000);tile_capture_health(health_now);return 1;
}
static void finish_product(void){
 queue.meta[40]++; /* products completed, including good products */
 if(best_slot>=0){
  queue.meta[M_EVENTS]++;queue.meta[41]++;best[8]=tile_event_with_reason(best[8],1);best[38]|=32; /* completed product */
  if(!queue_publish(&queue,(unsigned)best_slot,best))queue.meta[M_DROPPED]++;
  best_slot=-1;
 }
}
static void consume(unsigned slot,volatile uint32_t *trailer,XTime now){
 uint32_t w[DESC_WORDS];unsigned i,req=queue.meta[M_REQUEST],reason=queue.meta[M_REASON];
 for(i=0;i<DESC_WORDS;i++)w[i]=trailer[i];
 if(w[0]!=0x54465337u){queue.meta[M_INVALID]++;recovery_bad(&dma_recovery);return;}
 if(w[8]!=tile_descriptor_crc(w)){queue.meta[M_INVALID]++;queue.meta[M_DESC_CRC_ERRORS]++;recovery_bad(&dma_recovery);return;}
 if(w[35]!=FRAME_BYTES || (w[6]|w[9])&0x80000000u){queue.meta[M_INVALID]++;recovery_bad(&dma_recovery);return;}
 queue.meta[M_DESC_VERIFIED]++;queue.meta[M_LAST_DESC_CRC]=w[8];
 w[8]=tile_event_identity(dma_recovery.successes,0); /* PL CRC verified; bind this acquisition generation. */
 tile_slot_crc[slot]=w[1];
 w[1]=FRAME_BASE+slot*FRAME_STRIDE;w[34]=queue.meta[M_BOOT];w[36]=(uint32_t)(now/(COUNTS_PER_SECOND/1000));
 capture_health.valid=now;capture_health.seen_valid=1;
 queue.meta[M_CAPTURED]++;queue.meta[M_LAST_SEQ]=w[2];
 if(last_seq && w[2]>last_seq+1)queue.meta[M_GAPS]+=w[2]-last_seq-1;
 last_seq=w[2];queue.meta[42]=w[37];queue.meta[43]=w[38];
 recovery_good(&dma_recovery,now);
 // Verification frames are counted, but cannot be published as new evidence.
 if(dma_recovery.state!=REC_RUNNING)return;
 if(dma_recovery.wait_product && (w[38]&2))dma_recovery.wait_product=0;
 if(!dma_recovery.wait_product){
  if(w[38]&2){if(best_slot>=0){queue.meta[44]++;finish_product();}}
  if(w[38]&8){best_slot=(int)slot;memcpy(best,w,sizeof(best));queue.meta[45]++;}
  if(w[38]&4)finish_product();
 }
 if(req!=queue.meta[M_REQUEST_ACK]){
  w[8]=tile_event_with_reason(w[8],reason==1?2:3);
  if(queue_publish(&queue,slot,w))queue.meta[M_REQUEST_ACK]=req;
 }
}
static void acquisition(void){
 unsigned n,status,s,newslot;volatile uint32_t *bd;XTime now;
 for(n=0;n<BD_COUNT;n++){
  bd=(volatile uint32_t*)(BD_BASE+cursor*64);status=bd[7];
  if(!(status&0x80000000u))break;
  queue_barrier();s=(bd[2]-FRAME_BASE)/FRAME_STRIDE;dma_used&=~(1ULL<<s);XTime_GetTime(&now);capture_health.done=now;capture_health.seen_done=1;
  if((status&0x70000000u) || (status&0x03ffffffu)!=PACKET_BYTES || (status&0x0c000000u)!=0x0c000000u){queue.meta[M_INVALID]++;recovery_bad(&dma_recovery);}
  else consume(s,(volatile uint32_t*)(bd[2]+FRAME_BYTES),now);
  newslot=free_slot();if(newslot>=FRAME_SLOTS){queue.meta[M_ERRORS]=0xbad00001;return;}
  dma_used|=1ULL<<newslot;bd[2]=FRAME_BASE+newslot*FRAME_STRIDE;bd[7]=0;queue_barrier();
  Xil_Out32(DMA+0x40,BD_BASE+cursor*64);cursor=(cursor+1)%BD_COUNT;
 }
 if(n>queue.meta[46])queue.meta[46]=n;
 status=Xil_In32(DMA+0x34);
 if(status&0x770){queue.meta[M_ERRORS]=status;queue.meta[M_ACTIVE]=0;}
 queue.meta[M_FRAMES]=Xil_In32(0x41200000u);
}
static void fail_recovery(uint64_t now,uint32_t reason){
 recovery_failed(&dma_recovery,now,COUNTS_PER_SECOND/1000,reason);
 uint32_t cr=Xil_In32(DMA+0x30);
 Xil_Out32(CAP0+8,0);if(!(cr&4u))Xil_Out32(DMA+0x30,cr&~1u);queue.meta[M_ACTIVE]=0;
}
static void poll_recovery(uint64_t now,uint32_t sr,uint32_t cr){
 const uint64_t ticks_ms=COUNTS_PER_SECOND/1000;
 if(dma_recovery.state==REC_RUNNING){
  // Do not reset just because HDMI has not produced a frame or the input gate
  // was deliberately closed. Only an explicit DMA error or post-start halt.
  if((sr&0x770u) || (capture_health.seen_valid && (!(cr&1u)||(sr&1u)))){
   if(best_slot>=0 || queue.meta[42])dma_recovery.interrupted++;
   best_slot=-1; // Queue references remain independent and untouched.
   Xil_Out32(CAP0+8,0);queue.meta[M_ACTIVE]=0;
   if(recovery_begin(&dma_recovery,now,ticks_ms,(sr&0x770u)?REC_REASON_DMA_ERROR:REC_REASON_HALTED,sr))
    Xil_Out32(DMA+0x30,4); // Poll completion on later 10 ms passes; never spin.
  }
 }else if(dma_recovery.state==REC_RESETTING){
  if(now>=dma_recovery.deadline){fail_recovery(now,REC_REASON_RESET_TIMEOUT);return;}
  if(!(cr&4u)){
   if(!ring_populate()){fail_recovery(now,REC_REASON_NO_SLOTS);return;}
   recovery_verifying(&dma_recovery,now,ticks_ms);
   Xil_Out32(CAP0+8,2);queue.meta[M_ACTIVE]=1;
  }
 }else if(dma_recovery.state==REC_VERIFYING){
  if((sr&0x770u) || !(cr&1u) || (sr&1u)){fail_recovery(now,REC_REASON_REPEAT_DMA_ERROR);return;}
  if(dma_recovery.good>=2 && dma_recovery.verified_at<dma_recovery.deadline){recovery_success(&dma_recovery,now,ticks_ms);queue.meta[M_ERRORS]=0;queue.meta[M_ACTIVE]=1;}
  else if(now>=dma_recovery.deadline){fail_recovery(now,REC_REASON_VERIFY_TIMEOUT);return;}
 }
}
/* Reuse the network loop timestamp; sample registers/ages at most 100 Hz.
 * MMIO and 64-bit divisions stay out of the per-iteration fast path. */
void tile_capture_health(uint64_t now){
 uint32_t words[6],recovery_words[14],sr,cr;unsigned i;
 if(now-capture_health.published<10ULL*(COUNTS_PER_SECOND/1000))return;
 sr=Xil_In32(DMA+0x34);cr=Xil_In32(DMA+0x30);
 poll_recovery(now,sr,cr);
 if(dma_recovery.state==REC_RESETTING || dma_recovery.state==REC_FAILED)queue.meta[M_FRAMES]=Xil_In32(0x41200000u);
 health_snapshot(&capture_health,now,COUNTS_PER_SECOND/1000,sr,cr,queue.meta[M_ERRORS],words);
 if(dma_recovery.state==REC_RESETTING || dma_recovery.state==REC_VERIFYING)words[1]=6;
 else if(dma_recovery.state==REC_FAILED)words[1]=7;
 recovery_snapshot(&dma_recovery,recovery_words);
 for(i=0;i<14;i++)queue.meta[M_RECOVERY_BASE+i]=recovery_words[i];
 for(i=0;i<6;i++)queue.meta[M_HEALTH_BASE+i]=words[i];
 capture_health.published=now;
}
static void apply_recipe_if_idle(void){
 unsigned t=queue.meta[M_THRESHOLD];
 /* PL product identity is authoritative. Do not mix thresholds within a tile. */
 if(t>=1 && t<=255 && queue.meta[M_DETECT_MODE_REQUEST]<=2u && queue.meta[M_PRODUCT_GATE_REQUEST]<=1u &&
  queue.meta[M_WIDE_WEAK_REQUEST]<=1u &&
  (t!=threshold || queue.meta[M_DETECT_MODE_REQUEST]!=queue.meta[M_DETECT_MODE_APPLIED] ||
   queue.meta[M_PRODUCT_GATE_REQUEST]!=queue.meta[M_PRODUCT_GATE_APPLIED] ||
   queue.meta[M_WIDE_WEAK_REQUEST]!=queue.meta[M_WIDE_WEAK_APPLIED]) &&
  (queue.meta[42]==0 || (queue.meta[43]&4)))config(t);
}
int main(void){
 uint32_t boot;Xil_DCacheDisable();boot=Xil_In32(0x100000f0u);
 if(!boot || Xil_In32(0x100000f4u)!=(uint32_t)~boot){xil_printf("Boot identity missing: use this version's programming script\r\n");return 1;}
 queue_init(&queue,(volatile uint32_t*)0x10000000u,(volatile uint32_t*)0x10001000u,boot);
 Xil_Out32(CAP0+8,0);config(36);tile_network_start();
 if(!ring_start()){xil_printf("SG ring initialization failed\r\n");return 1;}
 queue.meta[M_ENABLE]=1;
 xil_printf("Tile V1.52 dual-scale weak PL; SG32 slots48; lossless TCP9133\r\n");
 for(;;){queue_ack(&queue);if(dma_recovery.state==REC_RUNNING || dma_recovery.state==REC_VERIFYING)acquisition();apply_recipe_if_idle();tile_network_poll();queue.meta[M_HEARTBEAT]++;}
}
int tile_network_maintenance_safe(void){return 1;}
