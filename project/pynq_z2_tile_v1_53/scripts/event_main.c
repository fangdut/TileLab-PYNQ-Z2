/* ARM schedules DMA and transports FPGA decisions, without image detection.
 * lscript.ld excludes DDR >=0x10000000. Disabling DCache ensures coherence
 * between CPU descriptors, FPGA DMA writes and external JTAG reads. */
#include "xil_io.h"
#include "xil_cache.h"
#include "xil_printf.h"
#include "xiltimer.h"
#include "sleep.h"
#include "event_queue.h"
#define DMA 0x40400000u
#define CAP0 0x41290000u
#define CAP1 0x412a0000u
#define CAP2 0x412b0000u
#define CAP3 0x412c0000u
#define REGIONS 0x43c00000u
static EventQueue queue;
static unsigned threshold=0,commit=0,token=0,slot=0,before=0,active=0,last_seq=0;
static XTime started;
static void config(unsigned t){
 unsigned word;commit^=0x80000000u;threshold=t;
 Xil_Out32(0x41210000u,0x00500050u);Xil_Out32(0x41210008u,0x027f04afu);
 word=commit|0x00f30007u|(t<<8);Xil_Out32(0x41200008u,word);queue.meta[M_CONFIG]=word;
}
static unsigned reset_dma(void){
 XTime now,t;XTime_GetTime(&t);Xil_Out32(DMA+0x30,4);
 do{XTime_GetTime(&now);if(now-t>COUNTS_PER_SECOND)return 0;}while(Xil_In32(DMA+0x30)&4);
 Xil_Out32(DMA+0x34,0x7000);Xil_Out32(DMA+0x30,1);return 1;
}
static void arm(void){
 slot=queue_free_slot(&queue);before=Xil_In32(CAP0);token=(Xil_In32(CAP0+8)^1u)&1u;
 Xil_Out32(DMA+0x34,0x7000);Xil_Out32(DMA+0x48,FRAME_BASE+slot*FRAME_STRIDE);
 Xil_Out32(DMA+0x58,FRAME_BYTES);queue_barrier();Xil_Out32(CAP0+8,token);
 active=1;queue.meta[M_ACTIVE]=1;XTime_GetTime(&started);
}
static void acquisition(void){
 uint32_t words[DESC_WORDS]={0};unsigned seq,status,dma,rseq,rstatus,request,reason,event,i;XTime now;
 if(!active){if(queue.meta[M_ENABLE])arm();return;}
 XTime_GetTime(&now);seq=Xil_In32(CAP0);status=Xil_In32(CAP2+8);dma=Xil_In32(DMA+0x34);
 if((status&0x80000000u && seq!=before && (status&1)==token) || (dma&0x70) || now-started>COUNTS_PER_SECOND){
  queue.meta[M_INVALID]++;queue.meta[M_ERRORS]=status;reset_dma();active=0;queue.meta[M_ACTIVE]=0;return;
 }
 if(seq==before || (status&1)!=token || !(status&4) || !(dma&2))return;
 rseq=Xil_In32(REGIONS);if(rseq!=seq)return;
 rstatus=Xil_In32(REGIONS+4);
 if(rstatus&0x80000000u){queue.meta[M_INVALID]++;active=0;queue.meta[M_ACTIVE]=0;return;}
 words[1]=FRAME_BASE+slot*FRAME_STRIDE;words[2]=seq;words[3]=Xil_In32(CAP1);
 words[4]=Xil_In32(CAP1+8);words[5]=Xil_In32(CAP2);words[6]=status;words[7]=Xil_In32(CAP3);words[9]=rstatus;
 for(i=0;i<16;i++)words[10+i]=Xil_In32(REGIONS+8+i*4);
 for(i=0;i<8;i++)words[26+i]=Xil_In32(REGIONS+72+i*4);
 if(Xil_In32(REGIONS)!=seq){queue.meta[M_INVALID]++;active=0;return;}
 queue.meta[M_CAPTURED]++;queue.meta[M_LAST_SEQ]=seq;
 if(last_seq && seq>last_seq+1)queue.meta[M_GAPS]+=seq-last_seq-1;last_seq=seq;
 event=queue_trigger(&queue,(rstatus&15)!=0 || (rstatus&256)!=0);
 request=queue.meta[M_REQUEST];reason=queue.meta[M_REASON];
 if(event || request!=queue.meta[M_REQUEST_ACK]){
  words[8]=event?1:(reason==1?2:3);words[34]=queue.meta[M_BOOT];words[35]=FRAME_BYTES;
  words[36]=(uint32_t)(now/(COUNTS_PER_SECOND/1000));
  if(queue_publish(&queue,slot,words)){if(request!=queue.meta[M_REQUEST_ACK])queue.meta[M_REQUEST_ACK]=request;}
  else if(event)queue.meta[M_DROPPED]++;
 }
 active=0;queue.meta[M_ACTIVE]=0;
}
int main(void){
 XTime now;uint32_t boot;Xil_DCacheDisable();XTime_GetTime(&now);
 boot=(uint32_t)now ^ Xil_In32(0x10000008u) ^ 0x13572468u;
 queue_init(&queue,(volatile uint32_t*)0x10000000u,(volatile uint32_t*)0x10001000u,boot);
 xil_printf("\r\nTile V1.3 PL regions8; event queue12; CPU DMA/transport only\r\n");
 config(36);if(!reset_dma()){xil_printf("DMA reset failed\r\n");return 1;}
 for(;;){
  unsigned t;queue_ack(&queue);t=queue.meta[M_THRESHOLD];
  if(!active && t>=1 && t<=255 && t!=threshold)config(t);
  acquisition();queue.meta[M_FRAMES]=Xil_In32(0x41200000u);queue.meta[M_HEARTBEAT]++;
  usleep(20);
 }
}
