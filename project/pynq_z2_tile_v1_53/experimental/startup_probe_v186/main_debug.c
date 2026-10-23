/* SPDX-License-Identifier: MIT
 * ARM transport/control only: no convolution, resize, feature, score or mask.
 * One request/connection, 64-byte LE header; payload CRC and header CRC.
 */
#include <stdint.h>
#include <string.h>
#include "lwip/init.h"
#include "lwip/tcp.h"
#include "lwip/priv/tcp_priv.h"
#include "lwip/etharp.h"
#include "lwip/ip4_frag.h"
#include "netif/xadapter.h"
#include "xil_cache.h"
#include "xil_mmu.h"
#include "xil_exception.h"
#include "xil_io.h"
#include "xil_printf.h"
#include "xiltimer.h"
#include "model_identity.h"
#define ID 0x17000001u
#define REQ 0x16905458u
#define REP 0x16905258u
#define IP 0x43c10000u
#define RGB 0x06000000u
#define OUT 0x07000000u
#define MODEL 0x08000000u
#define WORK 0x10000000u
#define STATUS 0x05f00000u
#define TRACE ((volatile uint64_t*)0x05f01000u)
static struct netif iface;
struct netif *echo_netif=&iface;
static struct tcp_pcb *client;
static uint32_t req[16],reply[16],rx_used,rx_bytes,rx_crc,tx_pos,tx_ack,tx_bytes;
static uint32_t upload_pos,model_ready,busy,boot,source_crc,reply_ready;
static uint32_t last_width,last_height,repeat_start,repeat_target,repeat_summary[16];
static uint32_t trace_step,trace_scores,trace_mask;
static unsigned char *rx_dst;
static const unsigned char *payload;
static uint32_t table[256];
static XTime fast,slow,link_time,started,elapsed,last_progress,last_poll;
static uint32_t crc_update(uint32_t c,const void *p,unsigned n){
 const unsigned char *s=p;while(n--)c=table[(c^*s++)&255]^(c>>8);return c;
}
static uint32_t crc(const void *p,unsigned n){
 uint32_t c=~0u,scratch[256];const unsigned char *src=p;
 if(n<=4096)return ~crc_update(c,p,n);
 /* Integrity only: read uncached DDR in words, CRC the cached scratch bytes. */
 while(n){unsigned count=n>sizeof(scratch)?sizeof(scratch):n;memcpy(scratch,src,count);c=crc_update(c,scratch,count);src+=count;n-=count;}
 return ~c;
}
static void lost(void *arg,err_t err){(void)arg;(void)err;client=0;reply_ready=0;}
static void abort_client(void){
 if(client){struct tcp_pcb *p=client;client=0;tcp_arg(p,0);tcp_recv(p,0);tcp_sent(p,0);tcp_err(p,0);tcp_abort(p);}reply_ready=0;
 /* A running IP retains exclusive ownership even if its peer disappears. */
}
static void respond(unsigned status,const void *data,unsigned bytes){
 unsigned i;for(i=0;i<16;i++)reply[i]=0;
 reply[0]=REP;reply[1]=status;reply[2]=req[2];reply[3]=bytes;
 reply[4]=data?crc(data,bytes):0;reply[5]=Xil_In32(0x41200000u);
 reply[6]=model_ready?MODEL_CRC:0;reply[7]=upload_pos;reply[8]=boot;
 reply[9]=(uint32_t)elapsed;reply[10]=(uint32_t)(elapsed>>32);
 reply[11]=COUNTS_PER_SECOND;reply[12]=source_crc;reply[13]=req[5];reply[14]=req[6];
 reply[15]=crc(reply,60);payload=data;tx_pos=tx_ack=0;tx_bytes=64+bytes;reply_ready=1;
 /* Long PL inference is allowed. Start the send timeout from the result,
  * rather than the last input packet several minutes earlier. */
 XTime_GetTime(&last_progress);
}
static void pump(void){
 if(!client||!reply_ready)return;
 while(tx_pos<tx_bytes){
  unsigned n=tx_pos<64?64-tx_pos:tx_bytes-tx_pos;
  const void *p=tx_pos<64?(const unsigned char*)reply+tx_pos:payload+tx_pos-64;
  unsigned space=tcp_sndbuf(client);if(n>space)n=space;if(n>4096)n=4096;if(!n)break;
  if(tcp_write(client,p,n,TCP_WRITE_FLAG_COPY)!=ERR_OK)break;tx_pos+=n;
 }tcp_output(client);
}
static err_t sent(void *arg,struct tcp_pcb *pcb,u16_t len){
 (void)arg;tx_ack+=len;XTime_GetTime(&last_progress);
 if(reply_ready&&tx_ack==tx_bytes){
  tcp_recv(pcb,0);tcp_sent(pcb,0);tcp_err(pcb,0);
  if(tcp_close(pcb)==ERR_OK){client=0;reply_ready=0;}else{tcp_recv(pcb,0);abort_client();return ERR_ABRT;}
 }else pump();return ERR_OK;
}
static void completed(void){
 if(req[3]&&(~rx_crc)!=req[7]){respond(4,0,0);return;}
 if(req[1]==1){respond(0,0,0);return;}
 if(req[1]==2){upload_pos=0;model_ready=0;respond(0,0,0);return;}
 if(req[1]==3){upload_pos+=req[3];respond(0,0,0);return;}
 if(req[1]==4){
  volatile uint32_t *m=(volatile uint32_t*)MODEL;
  if(upload_pos!=MODEL_BYTES||crc((const void*)MODEL,MODEL_BYTES)!=MODEL_CRC||m[0]!=ID||m[1]!=MODEL_BYTES||m[16]>0x08000000u){model_ready=0;respond(5,0,0);return;}
  model_ready=1;respond(0,0,0);return;
 }
 if(req[1]==5){
  source_crc=req[7];last_width=req[5];last_height=req[6];elapsed=0;
  /* Debug/control only: timestamps observe PL progress; no image arithmetic. */
  {unsigned i;for(i=0;i<100;i++)TRACE[i]=0;}
  trace_step=trace_scores=trace_mask=0;
  ((volatile uint32_t*)OUT)[16]=0xffffffffu;
  ((volatile uint32_t*)OUT)[16+MODEL_GRID*MODEL_GRID]=0xffffffffu;
  Xil_Out32(IP+0x10,MODEL);Xil_Out32(IP+0x14,0);
  Xil_Out32(IP+0x1c,WORK);Xil_Out32(IP+0x20,0);
  Xil_Out32(IP+0x28,RGB);Xil_Out32(IP+0x2c,0);
  Xil_Out32(IP+0x34,OUT);Xil_Out32(IP+0x38,0);
  Xil_Out32(IP+0x40,req[5]);Xil_Out32(IP+0x48,req[6]);
  __asm__ volatile("dsb sy" ::: "memory");
  busy=1;XTime_GetTime(&started);Xil_Out32(IP,1);
 }
 if(req[1]==6){
  repeat_start=((volatile uint32_t*)OUT)[9];repeat_target=req[4];elapsed=0;
  req[5]=last_width;req[6]=last_height;busy=2;XTime_GetTime(&started);
  Xil_Out32(IP,0x81u); /* PL auto-restart: no ARM start for subsequent frames. */
 }
}
static int start_request(void){
 if(req[0]!=REQ||req[15]!=crc(req,60)||req[1]<1||req[1]>6||Xil_In32(0x41200000u)!=ID)return 0;
 if(busy)return 0;
 rx_bytes=0;rx_crc=~0u;rx_dst=0;
 if(req[1]==6){if(req[3]||!model_ready||!last_width||!req[4]||req[4]>1000u)return 0;}
 else if(req[1]==1||req[1]==4){if(req[3])return 0;}
 else if(req[1]==2){if(req[3]||req[4]!=MODEL_BYTES||req[8]!=MODEL_CRC)return 0;}
 else if(req[1]==3){
  if(model_ready||req[4]!=upload_pos||!req[3]||req[3]>1048576u||req[3]>MODEL_BYTES-upload_pos)return 0;
  rx_dst=(unsigned char*)MODEL+upload_pos;
 }else{
  if(!model_ready||!req[5]||!req[6]||req[5]>1024||req[6]>1024||req[3]!=req[5]*req[6]*4u)return 0;
  rx_dst=(unsigned char*)RGB;
 }
 if(!req[3])completed();return 1;
}
static err_t received(void *arg,struct tcp_pcb *pcb,struct pbuf *p,err_t err){
 unsigned pos=0;(void)arg;
 if(err!=ERR_OK||!p){if(p)pbuf_free(p);abort_client();return ERR_ABRT;}
 XTime_GetTime(&last_progress);
 while(pos<p->tot_len){
  unsigned n=p->tot_len-pos;
  if(reply_ready||busy){pbuf_free(p);abort_client();return ERR_ABRT;}
  if(rx_used<64){
   if(n>64-rx_used)n=64-rx_used;pbuf_copy_partial(p,(unsigned char*)req+rx_used,n,pos);rx_used+=n;pos+=n;
   if(rx_used==64&&!start_request()){pbuf_free(p);abort_client();return ERR_ABRT;}
  }else{
   unsigned char temp[1024];if(n>sizeof(temp))n=sizeof(temp);
   if(n>req[3]-rx_bytes)n=req[3]-rx_bytes;
   if(!n||!rx_dst){pbuf_free(p);abort_client();return ERR_ABRT;}
   pbuf_copy_partial(p,temp,n,pos);memcpy(rx_dst+rx_bytes,temp,n);rx_crc=crc_update(rx_crc,temp,n);rx_bytes+=n;pos+=n;
   if(rx_bytes==req[3])completed();
  }
 }
 tcp_recved(pcb,p->tot_len);pbuf_free(p);pump();return ERR_OK;
}
static err_t accept_one(void *arg,struct tcp_pcb *pcb,err_t err){
 (void)arg;if(err!=ERR_OK||client||busy){tcp_abort(pcb);return ERR_ABRT;}
 client=pcb;rx_used=0;reply_ready=0;XTime_GetTime(&last_progress);
 tcp_recv(pcb,received);tcp_sent(pcb,sent);tcp_err(pcb,lost);tcp_nagle_disable(pcb);return ERR_OK;
}
/* Startup diagnosis only. User byte in SLCR REBOOT_STATUS persists across
 * non-POR resets. Preserve the lower24 hardware/BootROM status bits. */
static void startup_mark(unsigned stage){
 Xil_Out32(0xf8000008u,0xdf0du);
 unsigned reason=Xil_In32(0xf8000258u);
 Xil_Out32(0xf8000258u,(reason&0x00ffffffu)|((stage&255u)<<24));
 __asm__ volatile("dsb sy" ::: "memory");
 Xil_Out32(0xf8000004u,0x767bu);
}
int main(void){
 unsigned i,j,addr;ip_addr_t ip,mask,gw;XTime now;
 unsigned char mac[]={2,0x54,0x49,0x4c,1,0x69};struct tcp_pcb *listener;
 startup_mark(0xa1);Xil_DCacheDisable();startup_mark(0xa2);
 startup_mark(0xa3);boot=Xil_In32(STATUS+8);startup_mark(0xa4);
 if(!boot){startup_mark(0xe1);return 1;}
 startup_mark(0xa5);unsigned actual_id=Xil_In32(0x41200000u);startup_mark(0xa6);
 if(actual_id!=ID){startup_mark(0xe2);return 1;}
 for(i=0;i<256;i++){uint32_t c=i;for(j=0;j<8;j++)c=(c>>1)^((0u-(c&1))&0xedb88320u);table[i]=c;}
 for(addr=STATUS;addr<0x20000000u;addr+=0x100000u)Xil_SetTlbAttributes(addr,NORM_NONCACHE);
 startup_mark(0xa7);Xil_DCacheEnable();lwip_init();
 IP4_ADDR(&ip,192,168,33,10);IP4_ADDR(&mask,255,255,255,0);IP4_ADDR(&gw,0,0,0,0);
 startup_mark(0xa8);
 if(!xemac_add(&iface,&ip,&mask,&gw,mac,0xe000b000u)){startup_mark(0xe3);return 2;}
 startup_mark(0xa9);
 Xil_ExceptionEnable();netif_set_default(&iface);netif_set_up(&iface);
 listener=tcp_new();if(!listener||tcp_bind(listener,IP_ADDR_ANY,9136)!=ERR_OK)return 3;
 listener=tcp_listen(listener);if(!listener)return 4;tcp_accept(listener,accept_one);
 XTime_GetTime(&fast);slow=link_time=fast;
 Xil_Out32(STATUS,ID);Xil_Out32(STATUS+4,1);startup_mark(0xaa);
 xil_printf("V170 all-PL inference transport 192.168.33.10:9136\r\n");
 for(;;){
  XTime_GetTime(&now);
  if(now-fast>=COUNTS_PER_SECOND/4){tcp_fasttmr();fast=now;}
  if(now-slow>=COUNTS_PER_SECOND/2){tcp_slowtmr();slow=now;}
  if(now-link_time>=COUNTS_PER_SECOND){eth_link_detect(&iface);etharp_tmr();ip_reass_tmr();link_time=now;}
  xemacif_input(&iface);
  if(now-last_poll>=COUNTS_PER_SECOND/10000){
   last_poll=now;
   if(busy==1&&now>=started){
    unsigned step=((volatile uint32_t*)OUT)[8];
    if(step&&step<=96&&step!=trace_step){TRACE[step]=now-started;trace_step=step;}
    if(!trace_scores&&((volatile uint32_t*)OUT)[16]!=0xffffffffu){TRACE[97]=now-started;trace_scores=1;}
    if(!trace_mask&&((volatile uint32_t*)OUT)[16+MODEL_GRID*MODEL_GRID]!=0xffffffffu){TRACE[98]=now-started;trace_mask=1;}
   }
   if(busy==2 && ((volatile uint32_t*)OUT)[9]-repeat_start>=repeat_target){
    Xil_Out32(IP,0);busy=3; /* Disable restart, then drain the in-flight frame. */
   }
   if(busy==3 && (Xil_In32(IP)&4u)){
    unsigned i;busy=0;elapsed=now-started;
    for(i=0;i<16;i++)repeat_summary[i]=0;
    repeat_summary[0]=0x1700b001u;repeat_summary[1]=repeat_target;
    repeat_summary[2]=((volatile uint32_t*)OUT)[9]-repeat_start;
    repeat_summary[3]=repeat_start;repeat_summary[4]=((volatile uint32_t*)OUT)[9];
    repeat_summary[5]=source_crc;repeat_summary[6]=MODEL_CRC;
    if(client)respond(0,repeat_summary,sizeof(repeat_summary));
   }
   if(busy==1&&(Xil_In32(IP)&2u)){
    unsigned bytes;busy=0;elapsed=now-started;
    TRACE[99]=elapsed;
    __asm__ volatile("dsb sy" ::: "memory");
    bytes=(16u+MODEL_GRID*MODEL_GRID+req[5]*req[6])*4u;
    if(client)respond(((volatile uint32_t*)OUT)[1]?6:0,(const void*)OUT,bytes);
   }
   Xil_Out32(STATUS+12,busy);Xil_Out32(STATUS+16,((volatile uint32_t*)OUT)[8]);
  }
  /* Receive/send callbacks can timestamp progress after this loop's 'now'. */
  if(client&&!busy&&now>=last_progress&&now-last_progress>60ULL*COUNTS_PER_SECOND)abort_client();
  pump();
 }
}
