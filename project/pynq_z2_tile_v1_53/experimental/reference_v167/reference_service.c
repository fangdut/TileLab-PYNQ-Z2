/* Full-frame reference metric endpoint, separate from lossless capture 9133.
 * This revision accepts HOST-PREPARED alignment pairs on 9134. It does NOT
 * claim autonomous ARM registration. Every score/strong/weak bit comes from
 * the DDR FPGA accelerator. COPY-only TCP protects buffers across disconnect.
 */
#include <stdint.h>
#include <string.h>
#include "lwip/tcp.h"
#include "xil_io.h"
#include "xil_cache.h"
#include "xiltimer.h"
#define MAGIC 0x52463167u
#define ENGINE 0x43c10000u
#define INPUT_BYTES 2000000u
#define OUTPUT_BYTES 1000000u
static uint64_t paired[250000] __attribute__((aligned(64)));
static uint32_t scores[250000] __attribute__((aligned(64)));
static struct tcp_pcb *peer;
static uint32_t request[16],response[16];
static unsigned received,body,phase,tx,ack,total;
static XTime touched,started,finished;
static int running;
static uint32_t crc(const void *data,unsigned count){
 static uint32_t table[256];static unsigned ready;
 const unsigned char *p=data;uint32_t c=~0u;unsigned i,j;
 if(!ready){
  for(i=0;i<256;i++){uint32_t v=i;for(j=0;j<8;j++)v=(v>>1)^((0u-(v&1u))&0xedb88320u);table[i]=v;}
  ready=1;
 }
 for(i=0;i<count;i++)c=(c>>8)^table[(c^p[i])&255u];
 return ~c;
}
static void lost(void *arg,err_t err){
 (void)arg;(void)err;peer=0;phase=received=body=tx=ack=total=0;
 // Never recycle DDR while PL still owns it, even if the peer disappears.
}
static void abort_peer(void){if(peer){tcp_err(peer,0);tcp_recv(peer,0);tcp_sent(peer,0);tcp_abort(peer);}lost(0,0);}
static void reply(unsigned status,unsigned bytes){
 memset(response,0,sizeof(response));response[0]=MAGIC;response[1]=status;response[2]=request[2];response[3]=bytes;
 response[4]=bytes?crc(scores,bytes):0;response[5]=(uint32_t)(finished-started);response[6]=(uint32_t)((finished-started)>>32);
 response[7]=500;response[8]=500;response[9]=Xil_In32(0x43c00100u);response[10]=0x00016700;
 response[11]=request[4];response[12]=request[13];response[13]=request[14];response[14]=COUNTS_PER_SECOND;
 response[15]=crc(response,60);tx=ack=0;total=64+bytes;phase=3;
}
static err_t sent(void *arg,struct tcp_pcb *pcb,u16_t n){(void)arg;(void)pcb;ack+=n;XTime_GetTime(&touched);if(ack==total && tx==total)phase=4;return ERR_OK;}
static int valid(void){
 unsigned i;
 if(request[0]!=MAGIC || request[15]!=crc(request,60) || request[2]==0)return 0;
 if(request[1]==1)return request[3]==0;
 if(request[1]!=2 || request[3]!=INPUT_BYTES || request[11]!=18 || request[12]!=9)return 0;
 for(i=5;i<=7;i++)if(request[i]<205 || request[i]>320)return 0;
 for(i=8;i<=10;i++)if((int32_t)request[i]<-20 || (int32_t)request[i]>20)return 0;
 return Xil_In32(0x43c00100u)==0x16700601u;
}
static err_t receive(void *arg,struct tcp_pcb *pcb,struct pbuf *p,err_t error){
 unsigned pos=0,n;(void)arg;
 if(error!=ERR_OK || !p){if(p)pbuf_free(p);abort_peer();return ERR_ABRT;}
 XTime_GetTime(&touched);
 while(pos<p->tot_len){
  if(phase==0){
   n=64-received;if(n>p->tot_len-pos)n=p->tot_len-pos;
   pbuf_copy_partial(p,(unsigned char*)request+received,n,pos);pos+=n;received+=n;
   if(received==64){
    if(!valid()){pbuf_free(p);abort_peer();return ERR_ABRT;}
    if(request[1]==1){started=finished=0;reply(0,0);}
    else phase=1;
   }
  }else if(phase==1){
   n=INPUT_BYTES-body;if(n>p->tot_len-pos)n=p->tot_len-pos;
   pbuf_copy_partial(p,(unsigned char*)paired+body,n,pos);body+=n;pos+=n;
   if(body==INPUT_BYTES)phase=2;
  }else{pbuf_free(p);abort_peer();return ERR_ABRT;}
 }
 tcp_recved(pcb,p->tot_len);pbuf_free(p);return ERR_OK;
}
static err_t accept_one(void *arg,struct tcp_pcb *pcb,err_t error){
 (void)arg;if(error!=ERR_OK || peer || running){tcp_abort(pcb);return ERR_ABRT;}
 peer=pcb;phase=received=body=tx=ack=total=0;tcp_nagle_disable(pcb);tcp_recv(pcb,receive);tcp_sent(pcb,sent);tcp_err(pcb,lost);XTime_GetTime(&touched);return ERR_OK;
}
void reference_service_start(void){
 struct tcp_pcb *s=tcp_new();if(!s)return;
 if(tcp_bind(s,IP_ADDR_ANY,9134)!=ERR_OK){tcp_close(s);return;}
 s=tcp_listen(s);tcp_accept(s,accept_one);
}
void reference_service_poll(void){
 XTime now;unsigned n;const unsigned char *src;XTime_GetTime(&now);
 if(running){
  if(Xil_In32(ENGINE)&2u){
   running=0;finished=now;Xil_DCacheInvalidateRange((INTPTR)scores,OUTPUT_BYTES);
   if(peer)reply(0,OUTPUT_BYTES);
  }else if(now-started>5ULL*COUNTS_PER_SECOND){
   // Keep running ownership on a wedged engine until board reset. A timeout
   // cannot make unfinished DMA safe to overwrite with a new request.
   if(peer && phase==5){finished=now;reply(4,0);}
  }
 }
 if(!peer)return;
 if(now-touched>15ULL*COUNTS_PER_SECOND){abort_peer();return;}
 if(phase==2 && !running){
  if(crc(paired,INPUT_BYTES)!=request[4]){started=finished=0;reply(2,0);}
  else {
   Xil_DCacheFlushRange((INTPTR)paired,INPUT_BYTES);Xil_DCacheFlushRange((INTPTR)scores,OUTPUT_BYTES);
   // Generated HLS register offsets are checked against its driver header
   // during build; these are not inferred from GPIO or legacy captures.
   Xil_Out32(ENGINE+0x10,(uint32_t)(UINTPTR)paired);Xil_Out32(ENGINE+0x14,0);
   Xil_Out32(ENGINE+0x1c,(uint32_t)(UINTPTR)scores);Xil_Out32(ENGINE+0x20,0);
   for(n=0;n<8;n++)Xil_Out32(ENGINE+0x28+n*8,request[5+n]);
   XTime_GetTime(&started);Xil_Out32(ENGINE,1);running=1;phase=5;
  }
 }
 if(phase!=3 || tx==total)return;
 n=tx<64?64-tx:total-tx;if(n>2*TCP_MSS)n=2*TCP_MSS;if(n>tcp_sndbuf(peer))n=tcp_sndbuf(peer);if(!n)return;
 src=tx<64?(const unsigned char*)response+tx:(const unsigned char*)scores+tx-64;
 if(tcp_write(peer,src,n,TCP_WRITE_FLAG_COPY)==ERR_OK){tx+=n;tcp_output(peer);}
}
