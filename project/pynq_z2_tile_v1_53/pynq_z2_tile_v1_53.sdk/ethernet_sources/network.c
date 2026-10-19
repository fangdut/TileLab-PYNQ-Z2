/* Optional Ethernet transport. No vision/segmentation functions here.
 * lwIP raw API is single-threaded. One PC client; queue pins pixels until ACK.
 * Protocol is little endian, versioned, and restricted to a private lab LAN.
 */
#include <string.h>
#include "lwip/init.h"
#include "lwip/tcp.h"
#include "lwip/dhcp.h"
#include "lwip/etharp.h"
#include "lwip/ip4_frag.h"
#include "netif/xadapter.h"
#include "xiltimer.h"
#include "xil_exception.h"
#include "xil_cache.h"
#include "xil_mmu.h"
#include "xil_printf.h"
#include "xil_io.h"
#include "event_queue.h"
#include "network.h"
#include "word_rle.h"
#include "rle_probe.h"
#include "packed_pixels.h"
#include "packed_stream.h"
#include "header_crc.h"
extern EventQueue queue;
extern void tile_capture_health(uint64_t now);
extern uint32_t tile_slot_crc[FRAME_SLOTS];
extern void tcp_fasttmr(void),tcp_slowtmr(void);
static struct netif iface;
struct netif *echo_netif=&iface; /* required by AMD platform timer */
static struct tcp_pcb *client;
static uint32_t rx[4],header[69],rx_used,waiting,offset,total,acked,active,send_ready;
static unsigned char *pixels;
/* Cached scratch is linked below 0x10000000, outside PL's reserved slots.
 * One client/response at a time. Completed prefixes are copied into lwIP's
 * own pbuf storage: GEM may retain pbuf references even after TCP abort. */
static uint32_t encoded_pixels[FRAME_BYTES/4] __attribute__((aligned(64)));
static uint32_t input_chunk[2048] __attribute__((aligned(64)));
static WordRle encoder;
static PackedPixels packer;
static PackedFailure packed_failure;
static unsigned encoding,want_rle,want_packed,reply_codec;
static uint32_t reply_crc;
static XTime fast_time,slow_time,link_time,coarse_time,last_progress,last_pump;static unsigned ready;
#define PROTO 0x544c5033u
static void lost(void *arg,err_t err){(void)arg;(void)err;queue.meta[32]++;client=0;active=waiting=encoding=rx_used=send_ready=0;}
static void abort_client(void){if(client){tcp_arg(client,0);tcp_err(client,0);tcp_abort(client);}lost(0,0);}
static void pump(void){
 unsigned n,left,part,sent_any=0;const void *ptr;err_t e;u8_t flags;XTime now;
 if(!client || !active)return;
 /* Spread bursts over time instead of filling the entire TCP window in a
  * tight loop. This is a non-blocking upper bound, not a sleep in acquisition. */
 XTime_GetTime(&now);
 if(now-last_pump<50ULL*(COUNTS_PER_SECOND/1000000))return;
 /* Bounded work keeps the DMA acquisition loop responsive. Pixel buffers are
  * pinned by the event queue until application ACK, after TCP ACK of all bytes.
  * Abort frees TCP references but deliberately leaves the event queued. */
 for(part=0;part<1 && offset<total && offset<send_ready;part++){
  left=offset<sizeof(header)?sizeof(header)-offset:total-offset;
  if(left>send_ready-offset)left=send_ready-offset;
  n=tcp_sndbuf(client);if(n>2*TCP_MSS)n=2*TCP_MSS;if(n>left)n=left;if(!n)break;
  ptr=offset<sizeof(header)?(const unsigned char*)header+offset:pixels+offset-sizeof(header);
  if(offset>=sizeof(header) && reply_codec==0){
   /* lwIP's payload destination may be unaligned. A bytewise copy directly
    * from uncached DDR is very slow, so first burst into the existing aligned
    * cached chunk. Keep RAW offsets word-aligned even for odd TCP windows.
    * tcp_write(COPY) consumes this temporary synchronously before reuse. */
   n&=~3u;if(!n)break;
   memcpy(input_chunk,ptr,n);ptr=input_chunk;
  }
  /* COPY is required for payload too. The GEM driver retains pbufs until TX
   * completion; tcp_abort alone cannot prove application RAM is no longer
   * referenced by a hardware descriptor. Its pbuf reference now keeps the
   * copied bytes alive while acquisition/retries reuse application scratch.
   * Copy work is bounded above by the same two-MSS pump budget. */
  flags=TCP_WRITE_FLAG_COPY;
  if(offset+n<total)flags|=TCP_WRITE_FLAG_MORE;
  e=tcp_write(client,ptr,n,flags);if(e!=ERR_OK){queue.meta[30]++;break;}
  offset+=n;sent_any=1;last_pump=now;
 }
 if(sent_any && tcp_output(client)!=ERR_OK)queue.meta[31]++;
}
static err_t sent(void *arg,struct tcp_pcb *pcb,u16_t len){
 (void)arg;(void)pcb;acked+=len;XTime_GetTime(&last_progress);
 if(acked==total && offset==total)active=0;
 return ERR_OK;
}
static void reply(unsigned code,unsigned bytes){
 unsigned i;header[0]=PROTO;header[1]=code;header[2]=bytes;header[3]=5|(code==0?(2|8|(reply_codec<<8)):0);
 for(i=0;i<24;i++)header[44+i]=queue.meta[i];
 /* Frame flag bit 1 replaces response heartbeat with the PL pixel CRC.
  * Status replies retain their original heartbeat and flags. */
 if(code==0)header[47]=reply_crc;
 /* Bit 2 announces a trailing header CRC after the legacy 68 words. All
  * response types include it; descriptor, identity, size and pixel CRC bind
  * to this exact snapshot. Payload still follows sizeof(header). */
 header[68]=tile_header_crc(header,68);
 offset=acked=0;total=sizeof(header)+bytes;send_ready=total;active=1;waiting=0;
}
static void start_packed(void){
 packed_begin(&packer,(const uint32_t*)pixels,FRAME_BYTES/4,encoded_pixels,FRAME_BYTES);
 pixels=(unsigned char*)encoded_pixels;encoding=2;reply_codec=2;
 reply(0,packer.bytes);
 send_ready=packed_stream_ready(sizeof(header),packer.words,packer.pos,packer.done,packer.failed);
}
static err_t received(void *arg,struct tcp_pcb *pcb,struct pbuf *p,err_t err){
 unsigned char data[16];unsigned n;(void)arg;
 if(err!=ERR_OK){if(p)pbuf_free(p);abort_client();return ERR_ABRT;}
 if(!p){abort_client();return ERR_ABRT;}
 XTime_GetTime(&last_progress);
 if(p->tot_len>16-rx_used){pbuf_free(p);abort_client();return ERR_ABRT;}
 n=pbuf_copy_partial(p,data,p->tot_len,0);tcp_recved(pcb,p->tot_len);pbuf_free(p);
 memcpy((unsigned char*)rx+rx_used,data,n);rx_used+=n;
 if(rx_used<16){return ERR_OK;}
 rx_used=0;
 if(rx[0]!=PROTO || active || waiting || encoding){abort_client();return ERR_ABRT;}
 queue.meta[M_PL_MODEL]=Xil_In32(0x43c00100u);
 memset(header,0,sizeof(header));
 /* V164 single-fixture firmware freezes the detector profile. Legacy mode
  * changes are rejected before any configuration state is written. */
 if((rx[1]==1u || rx[1]==5u) &&
    (rx[2]!=90u || (rx[1]==5u ? rx[3]!=612u :
     ((rx[3]&~10u)!=612u || ((rx[3]&8u) && !(rx[3]&2u)))))){
  reply(2,0);return ERR_OK;
 }

 if(rx[1]==1 && rx[2]>=1 && rx[2]<=255 && rx[3]<=1023 && (rx[3]&5)!=5 &&
    ((rx[3]&384)!=384) && (!(rx[3]&512) || ((rx[3]&484)==100 && rx[2]==90 && !(rx[3]&1) && queue.meta[M_PL_MODEL]==TILE_MODEL_ID)) && (!(rx[3]&384) || ((rx[3]&100)==100 && rx[2]==90 && !(rx[3]&1))) &&
    (!(rx[3]&64) || (rx[2]==90 && (rx[3]&36)==36 && !(rx[3]&1))) &&
    (!(rx[3]&8) || (rx[3]&2)) && (!(rx[3]&32) || ((rx[3]&4) && !(rx[3]&1)))){
  // Bits 0=disable growth, 1=RLE, 2=four-pass, 3=accept PACK25,
  // 4=low product gate, 5=radius-16 weak support (requires four-pass growth).
  // 6=directional mean candidate (fixed T90, wide support and four-pass).
  // Older clients never set bit 3 and keep RAW32/WORD_RLE responses.
  // Apply together with the threshold only at the existing product gap.
  want_rle=(rx[3]>>1)&1;want_packed=(rx[3]>>3)&1;reply_codec=0;
  queue.meta[M_THRESHOLD]=rx[2];queue.meta[M_DETECT_MODE_REQUEST]=(rx[3]&4)?2:(rx[3]&1);queue.meta[M_PRODUCT_GATE_REQUEST]=(rx[3]>>4)&1;
  queue.meta[M_WIDE_WEAK_REQUEST]=(rx[3]>>5)&1;queue.meta[M_RIDGE_REQUEST]=(rx[3]>>6)&1;queue.meta[M_WIDE_LINE_REQUEST]=(rx[3]>>7)&1;queue.meta[M_DIRECTIONAL_REQUEST]=(rx[3]>>8)&1;queue.meta[M_BOOST_REQUEST]=(rx[3]>>9)&1;queue.meta[M_ENABLE]=1;waiting=1;
  if(queue.head==queue.tail){queue.meta[M_REASON]=2;queue.meta[M_REQUEST]=queue.meta[M_REQUEST_ACK]+1;}
 }else if(rx[1]==5 && rx[2]>=1 && rx[2]<=255 &&
  (rx[3]==0 || rx[3]==1 || rx[3]==4 || rx[3]==16 || rx[3]==17 || rx[3]==20 || rx[3]==36 || rx[3]==52 ||
   (rx[2]==90 && (rx[3]==100 || rx[3]==116 || rx[3]==228 || rx[3]==244 || rx[3]==356 || rx[3]==372 || ((rx[3]==612 || rx[3]==628) && queue.meta[M_PL_MODEL]==TILE_MODEL_ID))))){
  /* Configure inspection without requesting a full preview frame. The main
   * loop still commits threshold/support mode only between physical tiles. */
  queue.meta[M_THRESHOLD]=rx[2];queue.meta[M_DETECT_MODE_REQUEST]=(rx[3]&4)?2:(rx[3]&1);queue.meta[M_PRODUCT_GATE_REQUEST]=(rx[3]>>4)&1;
  queue.meta[M_WIDE_WEAK_REQUEST]=(rx[3]>>5)&1;queue.meta[M_RIDGE_REQUEST]=(rx[3]>>6)&1;queue.meta[M_WIDE_LINE_REQUEST]=(rx[3]>>7)&1;queue.meta[M_DIRECTIONAL_REQUEST]=(rx[3]>>8)&1;queue.meta[M_BOOST_REQUEST]=(rx[3]>>9)&1;queue.meta[M_ENABLE]=1;
  reply(1,0);
 }else if(rx[1]==2){
  /* Reject future/stale/wrong-boot requests before touching the ACK mailbox.
   * A duplicate committed head is harmless; the next ID needs a real front. */
  if(rx[2]!=queue.meta[M_BOOT] || (rx[3]!=queue.head && (queue.head==queue.tail || rx[3]!=queue.head+1))){
   queue.meta[M_ACK_ERRORS]++;reply(2,0);
  }else{
   if(rx[3]!=queue.head){queue.meta[M_ACK]=rx[3];queue_ack(&queue);}
   reply(queue.head==rx[3]?1:2,0);
  }
 }else if(rx[1]==3){
  for(n=0;n<40;n++)header[4+n]=queue.meta[24+n];
  /* V1.32 status-only overlay. Op4 keeps the original timing diagnostics;
   * frame descriptors and the 276-byte CRC-protected header are unchanged. */
  header[4+37]=queue.meta[M_PL_MODEL];header[4+38]=TILE_MODEL_ID;
  for(n=0;n<6;n++)header[4+n]=queue.meta[M_HEALTH_BASE+n];
  for(n=0;n<14;n++)header[4+23+n]=queue.meta[M_RECOVERY_BASE+n];
  reply(1,0);
 }

 else if(rx[1]==6){
  uint32_t lo=Xil_In32(0x41210000u),hi=Xil_In32(0x41210008u);
  header[4]=TILE_SINGLE_PROFILE_ID;header[5]=lo;header[6]=hi;
  header[7]=queue.meta[M_PL_MODEL];header[8]=TILE_SINGLE_SIDE;
  header[9]=TILE_SINGLE_FIRMWARE_VERSION;
  header[10]=(lo==TILE_SINGLE_ROI_MIN && hi==TILE_SINGLE_ROI_MAX && queue.meta[M_PL_MODEL]==TILE_MODEL_ID);
  /* GPIO echoes are request-register readback; frame config is checked again
   * in every delivered evidence packet after PL frame-boundary application. */
  reply(1,0);
 }
 else if(rx[1]==4){for(n=0;n<40;n++)header[4+n]=queue.meta[24+n];reply(1,0);}
 else reply(2,0);
 return ERR_OK;
}
static err_t accept_one(void *arg,struct tcp_pcb *pcb,err_t err){
 (void)arg;if(err!=ERR_OK || client){tcp_abort(pcb);return ERR_ABRT;}
 client=pcb;queue.meta[33]++;rx_used=waiting=encoding=active=0;XTime_GetTime(&last_progress);tcp_recv(pcb,received);tcp_sent(pcb,sent);tcp_err(pcb,lost);tcp_nagle_disable(pcb);return ERR_OK;
}
void tile_network_start(void){
 ip_addr_t ip,mask,gw;unsigned char mac[]={0x02,0x54,0x49,0x4c,0x01,0x03};struct tcp_pcb *listen;
 volatile const uint32_t *cfg=(volatile const uint32_t*)0x10000400u;
 unsigned addr,direct=(cfg[0]==0x544e4554u && cfg[1]!=0 && cfg[4]==~cfg[1]);
 /* main enters with DCache off. Keep metadata, SG descriptors and 48 slots uncached;
  * enable caching only for ordinary code/data, heap and lwIP packet buffers.
  * The AMD GEM driver maintains cache coherence for its own DMA buffers. */
 for(addr=0x10000000u;addr<0x1d000000u;addr+=0x100000u)Xil_SetTlbAttributes(addr,NORM_NONCACHE);
 Xil_DCacheEnable();lwip_init();IP4_ADDR(&ip,0,0,0,0);IP4_ADDR(&mask,0,0,0,0);IP4_ADDR(&gw,0,0,0,0);
 if(direct){
  IP4_ADDR(&ip,(cfg[1]>>24)&255,(cfg[1]>>16)&255,(cfg[1]>>8)&255,cfg[1]&255);
  IP4_ADDR(&mask,255,255,0,0); /* Direct PC link: APIPA /16, no router needed. */
 }
 if(!xemac_add(&iface,&ip,&mask,&gw,mac,0xe000b000u)){xil_printf("ETH init failed\r\n");return;}
 Xil_ExceptionEnable();
 netif_set_default(&iface);netif_set_up(&iface);if(!direct)dhcp_start(&iface);
 listen=tcp_new();if(!listen || tcp_bind(listen,IP_ADDR_ANY,9133)!=ERR_OK){xil_printf("ETH bind failed\r\n");return;}
 listen=tcp_listen(listen);tcp_accept(listen,accept_one);
 XTime_GetTime(&fast_time);slow_time=link_time=coarse_time=fast_time;ready=1;
 xil_printf("ETH %s / TCP 9133\r\n",direct?"direct static /16":"DHCP");
}
void tile_network_poll(void){
 unsigned i;static unsigned announced=0;XTime now,t,end,begin;
 if(!ready){return;}
 XTime_GetTime(&now);
 begin=now;tile_capture_health(now);
 /* Release a vanished peer without releasing its unacknowledged evidence. */
 if(client){
  queue.meta[47]=offset;queue.meta[48]=acked;queue.meta[49]=total;
  queue.meta[50]=client->lastack;queue.meta[51]=client->snd_nxt;
  queue.meta[52]=client->snd_buf;queue.meta[53]=client->cwnd;queue.meta[54]=client->snd_wnd;
  queue.meta[55]=client->nrtx;queue.meta[56]=(uint32_t)client->rtime;queue.meta[57]=client->rto;
  queue.meta[58]=client->dupacks;queue.meta[59]=client->unsent!=0;queue.meta[60]=client->unacked!=0;
  if(client->nrtx>queue.meta[34])queue.meta[34]=client->nrtx;
  if(active && (unsigned)((now-last_progress)/(COUNTS_PER_SECOND/1000))>queue.meta[35])queue.meta[35]=(unsigned)((now-last_progress)/(COUNTS_PER_SECOND/1000));
  if(now-last_progress>(active||waiting||encoding?2ULL:30ULL)*COUNTS_PER_SECOND){queue.meta[36]++;abort_client();}
 }
 /* Poll the existing Cortex-A9 global timer. No extra TTC/IP or timer ISR. */
 /* SG has a pre-posted multi-frame queue, so timers run at their regular
  * deadlines, independently of video sync and HDMI lock. */
 if(tile_network_maintenance_safe()){
  if(now-fast_time>=(COUNTS_PER_SECOND)/4){XTime_GetTime(&t);tcp_fasttmr();XTime_GetTime(&end);i=(unsigned)((end-t)/(COUNTS_PER_SECOND/1000000));if(i>queue.meta[24])queue.meta[24]=i;fast_time=now;}
  if(now-slow_time>=(COUNTS_PER_SECOND)/2){XTime_GetTime(&t);tcp_slowtmr();dhcp_fine_tmr();XTime_GetTime(&end);i=(unsigned)((end-t)/(COUNTS_PER_SECOND/1000000));if(i>queue.meta[25])queue.meta[25]=i;slow_time=now;}
  if(now-coarse_time>=(COUNTS_PER_SECOND)*60ULL){dhcp_coarse_tmr();coarse_time=now;}
  if(now-link_time>=(COUNTS_PER_SECOND)){XTime_GetTime(&t);eth_link_detect(&iface);etharp_tmr();ip_reass_tmr();XTime_GetTime(&end);i=(unsigned)((end-t)/(COUNTS_PER_SECOND/1000000));if(i>queue.meta[26])queue.meta[26]=i;link_time=now;}
 }
 XTime_GetTime(&t);
 xemacif_input(&iface);
 XTime_GetTime(&end);i=(unsigned)((end-t)/(COUNTS_PER_SECOND/1000000));if(i>queue.meta[27])queue.meta[27]=i;
 if(!announced && !ip4_addr_isany_val(*netif_ip4_addr(&iface))){
  const ip4_addr_t *a=netif_ip4_addr(&iface);xil_printf("ETH address=%d.%d.%d.%d port=9133\r\n",ip4_addr1(a),ip4_addr2(a),ip4_addr3(a),ip4_addr4(a));announced=1;
 }
 if(waiting && queue.head!=queue.tail){
  volatile uint32_t *d=queue_front(&queue);
  for(i=0;i<DESC_WORDS;i++){header[4+i]=d[i];}
  pixels=(unsigned char*)d[1];reply_codec=0;
  reply_crc=tile_slot_crc[(d[1]-FRAME_BASE)/FRAME_STRIDE];
  if(packed_failure_matches(&packed_failure,queue.meta[M_BOOT],d,reply_crc)){
   reply(0,FRAME_BYTES);
  }else if(want_rle && tile_rle_worthwhile((const uint32_t*)pixels,FRAME_BYTES/4)){
   rle_begin(&encoder,(const uint32_t*)pixels,FRAME_BYTES/4,encoded_pixels,FRAME_BYTES/4);waiting=0;encoding=1;
  }else{
   if(want_rle)queue.meta[63]++; /* V1.32: raw bypasses selected by the probe */
   if(want_packed)start_packed();
   else reply(0,FRAME_BYTES);
  }
 }
 if(encoding==1){
  /* Burst copy the uncached DMA slot into a small cached block. Processing
   * uncached pixels individually otherwise costs one DDR transaction each.
   * DMA memory attributes/ownership are unchanged; no cache aliases. */
  unsigned chunk=encoder.words-encoder.pos;if(chunk>2048)chunk=2048;
  memcpy(input_chunk,encoder.src+encoder.pos,chunk*4);
  if(rle_feed(&encoder,input_chunk,chunk)){
  encoding=0;
  /* Never grow the wire payload; tiny savings do not justify a new encoding. */
  if(!encoder.failed && encoder.out<FRAME_BYTES/4-FRAME_BYTES/80 && (!want_packed || encoder.out*4<packed_size(FRAME_BYTES/4))){pixels=(unsigned char*)encoded_pixels;reply_codec=1;reply(0,encoder.out*4);}
  else if(want_packed)start_packed();
  else reply(0,FRAME_BYTES);
  }
 }
 else if(encoding==2){
  unsigned chunk=packer.words-packer.pos;if(chunk>2048)chunk=2048;
  memcpy(input_chunk,packer.src+packer.pos,chunk*4);
  packed_feed(&packer,input_chunk,chunk);
  if(packer.failed){
   packed_failure_set(&packed_failure,header[46],header+4,reply_crc);
   /* A header or prefix may already have gone out. Never switch codecs in
    * that response. Abort TCP references; keep the event for a RAW retry. */
   abort_client();
  }else{
   send_ready=packed_stream_ready(sizeof(header),packer.words,packer.pos,packer.done,0);
   if(packer.done)encoding=0;
  }
 }
 XTime_GetTime(&t);pump();XTime_GetTime(&end);i=(unsigned)((end-t)/(COUNTS_PER_SECOND/1000000));if(i>queue.meta[28])queue.meta[28]=i;
 i=(unsigned)((end-begin)/(COUNTS_PER_SECOND/1000000));if(i>queue.meta[29])queue.meta[29]=i;
}
