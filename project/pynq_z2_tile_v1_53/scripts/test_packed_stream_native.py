"""Compile the actual network.c against bounded, reference-holding TCP stubs.

This is a native ownership/protocol test, not a network-speed measurement.
The Windows process maps an isolated fake slot at the firmware's address.
No JTAG/device access is performed.
"""
from pathlib import Path
import hashlib,json,subprocess,sys
R=Path(__file__).resolve().parents[1]; S=R/(R.name+'.sdk')/'ethernet_sources'
old_dma='--expect-dma-counterexample' in sys.argv
network=R/'reports/v132_nocopy_trial/firmware_snapshot/network.c' if old_dma else S/'network.c'
O=R/('reports/v137/native_dma_counterexample' if old_dma else 'reports/v137/native_stream');O.mkdir(parents=True,exist_ok=True)
stub=r'''
#ifndef TEST_STUB_H
#define TEST_STUB_H
#include <stdint.h>
#include <string.h>
typedef uint64_t XTime;
typedef unsigned char u8_t; typedef unsigned short u16_t; typedef int err_t;
#define COUNTS_PER_SECOND 1000000ULL
#define TCP_MSS 1460
#define ERR_OK 0
#define ERR_ABRT -1
#define ERR_MEM -2
#define TCP_WRITE_FLAG_COPY 1
#define TCP_WRITE_FLAG_MORE 2
#define NORM_NONCACHE 0
typedef uint32_t ip_addr_t;typedef uint32_t ip4_addr_t;
struct netif {ip4_addr_t ip;};
struct pbuf {u16_t tot_len;void *payload;};
struct tcp_pcb {unsigned lastack,snd_nxt,snd_buf,cwnd,snd_wnd,nrtx,rtime,rto,dupacks;void *unsent,*unacked;};
static XTime tick;
static inline void XTime_GetTime(XTime *p){tick+=10;*p=tick;}
static inline unsigned tcp_sndbuf(struct tcp_pcb *p){return p->snd_buf;}
err_t tcp_write(struct tcp_pcb*,const void*,u16_t,u8_t);
err_t tcp_output(struct tcp_pcb*);
void tcp_abort(struct tcp_pcb*);
static inline void tcp_arg(struct tcp_pcb*p,void*a){(void)p;(void)a;}
static inline void tcp_err(struct tcp_pcb*p,void(*f)(void*,err_t)){(void)p;(void)f;}
static inline void tcp_recv(struct tcp_pcb*p,err_t(*f)(void*,struct tcp_pcb*,struct pbuf*,err_t)){(void)p;(void)f;}
static inline void tcp_sent(struct tcp_pcb*p,err_t(*f)(void*,struct tcp_pcb*,u16_t)){(void)p;(void)f;}
static inline void tcp_accept(struct tcp_pcb*p,err_t(*f)(void*,struct tcp_pcb*,err_t)){(void)p;(void)f;}
static inline void tcp_nagle_disable(struct tcp_pcb*p){(void)p;}
static inline void tcp_recved(struct tcp_pcb*p,unsigned n){(void)p;(void)n;}
static inline unsigned pbuf_copy_partial(struct pbuf*p,void*d,unsigned n,unsigned off){memcpy(d,(char*)p->payload+off,n);return n;}
static inline void pbuf_free(struct pbuf*p){(void)p;}
static inline void Xil_SetTlbAttributes(unsigned a,unsigned b){(void)a;(void)b;}
static inline void Xil_DCacheEnable(void){}
static inline void Xil_ExceptionEnable(void){}
static inline void lwip_init(void){}
#define IP4_ADDR(p,a,b,c,d) (*(p)=((a)<<24)|((b)<<16)|((c)<<8)|(d))
#define IP_ADDR_ANY 0
static inline struct netif *xemac_add(struct netif*n,ip_addr_t*a,ip_addr_t*b,ip_addr_t*c,unsigned char*d,unsigned e){(void)a;(void)b;(void)c;(void)d;(void)e;return n;}
static inline void netif_set_default(struct netif*n){(void)n;}
static inline void netif_set_up(struct netif*n){(void)n;}
static inline void dhcp_start(struct netif*n){(void)n;}
static inline struct tcp_pcb *tcp_new(void){return 0;}
static inline err_t tcp_bind(struct tcp_pcb*p,unsigned a,unsigned b){(void)p;(void)a;(void)b;return 0;}
static inline struct tcp_pcb *tcp_listen(struct tcp_pcb*p){return p;}
static inline void xil_printf(const char*s,...){(void)s;}
static inline void tcp_fasttmr(void){}
static inline void tcp_slowtmr(void){}
static inline void dhcp_fine_tmr(void){}
static inline void dhcp_coarse_tmr(void){}
static inline void eth_link_detect(struct netif*n){(void)n;}
static inline void etharp_tmr(void){}
static inline void ip_reass_tmr(void){}
static inline void xemacif_input(struct netif*n){(void)n;}
#define netif_ip4_addr(n) (&(n)->ip)
#define ip4_addr_isany_val(a) (!(a))
#define ip4_addr1(a) (0)
#define ip4_addr2(a) (0)
#define ip4_addr3(a) (0)
#define ip4_addr4(a) ((int)*(a))
#endif
'''
(O/'stub.h').write_text(stub)
for name in ['lwip/init.h','lwip/tcp.h','lwip/dhcp.h','lwip/etharp.h','lwip/ip4_frag.h','netif/xadapter.h','xiltimer.h','xil_exception.h','xil_cache.h','xil_mmu.h','xil_printf.h']:
 p=O/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text('#include "stub.h"\n')
c=r'''
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include "network.c"
EventQueue queue;
uint32_t tile_slot_crc[FRAME_SLOTS];
static unsigned health_calls;
void tile_capture_health(uint64_t t){(void)t;health_calls++;}
int tile_network_maintenance_safe(void){return 1;}
static uint32_t metadata[META_WORDS],descriptors[QUEUE_CAPACITY*DESC_WORDS];
static uint32_t *source;
static struct tcp_pcb peer;
typedef struct {const unsigned char *ref;unsigned char copy[2*TCP_MSS];unsigned n,flags;} Borrow;
static Borrow borrowed[64];static unsigned nr,wire_n,writes,aborts,polls,scenario;
static Borrow hardware[64];static unsigned hardware_n,retain_after_abort,hardware_checks;
static unsigned copied_payload_writes,borrowed_payload_writes;
static unsigned char wire[FRAME_BYTES+512],expected[FRAME_BYTES];
static unsigned overlap_seen,held_checks,roundtrips,retries,pre_header_fail,late_fail;
static void check_hardware(void){unsigned i;for(i=0;i<hardware_n;i++){
 if(memcmp(hardware[i].copy,hardware[i].ref,hardware[i].n)){
  fprintf(stderr,"COUNTEREXAMPLE GEM reference changed after TCP abort and legitimate next-event encoding\n");exit(41);
 }hardware_checks++;
}}
static void check_borrows(void){unsigned i;for(i=0;i<nr;i++)if(!(borrowed[i].flags&TCP_WRITE_FLAG_COPY)){
 assert(!memcmp(borrowed[i].copy,borrowed[i].ref,borrowed[i].n));held_checks++;
}}
err_t tcp_write(struct tcp_pcb*p,const void*data,u16_t n,u8_t flags){
 Borrow*b;writes++;if((writes+scenario)%23==0)return ERR_MEM;
 assert(n<=2*TCP_MSS && n<=p->snd_buf && nr<64);assert(offset+n<=send_ready && offset+n<=total);
 if(offset>=sizeof(header)){if(flags&TCP_WRITE_FLAG_COPY)copied_payload_writes++;else borrowed_payload_writes++;
 #ifndef EXPECT_OLD_DMA_LIFETIME
  if(reply_codec==0){assert(data==(const void*)input_chunk && !(n&3u) && !(offset&3u));}
 #endif
 }
 if(encoding==2 && offset>=sizeof(header)){
  assert(offset+n<=sizeof(header)+3*packer.pos);assert(!packer.done);overlap_seen++;
 }
 b=&borrowed[nr++];b->ref=data;b->n=n;b->flags=flags;memcpy(b->copy,data,n);p->snd_buf-=n;return ERR_OK;
}
err_t tcp_output(struct tcp_pcb*p){(void)p;return writes%71?ERR_OK:ERR_MEM;}
void tcp_abort(struct tcp_pcb*p){unsigned i;(void)p;check_borrows();
 if(retain_after_abort && nr){assert(!hardware_n);for(i=0;i<nr;i++){
  hardware[i]=borrowed[i];
  /* COPY belongs to lwIP's pbuf; the GEM reference keeps that storage alive.
   * Without COPY the retained descriptor still points into application RAM. */
  if(hardware[i].flags&TCP_WRITE_FLAG_COPY)hardware[i].ref=hardware[i].copy;
 }hardware_n=nr;retain_after_abort=0;}
 nr=0;aborts++;
}
static void ack_one(void){Borrow b;if(!nr)return;check_borrows();b=borrowed[0];
 assert(wire_n+b.n<=sizeof(wire));memcpy(wire+wire_n,b.copy,b.n);wire_n+=b.n;
 memmove(borrowed,borrowed+1,(--nr)*sizeof(Borrow));peer.snd_buf+=b.n;sent(0,&peer,(u16_t)b.n);
}
static void connect_peer(void){assert(!client && !nr);memset(&peer,0,sizeof(peer));peer.snd_buf=12000+scenario%4;wire_n=0;assert(accept_one(0,&peer,ERR_OK)==ERR_OK);}
static void request(unsigned flags){uint32_t q[4]={PROTO,1,90,flags};struct pbuf p={16,q};assert(received(0,&peer,&p,ERR_OK)==ERR_OK);}
static void poll_once(void){unsigned old=packer.pos,was=encoding;check_borrows();tile_network_poll();polls++;check_hardware();
 if(was==2 && encoding==2)assert(packer.pos>=old && packer.pos-old<=2048);
 if(polls%5==0 || nr>5)ack_one();
}
static void finish(void){unsigned limit=100000;while(client&&(active||encoding||waiting||nr)&&--limit)poll_once();assert(limit);check_borrows();}
static void fill(unsigned seed){unsigned i;uint32_t v=seed;for(i=0;i<FRAME_BYTES/4;i++){v^=v<<13;v^=v>>17;v^=v<<5;source[i]=v&0x1ffffffu;}tile_slot_crc[0]=tile_header_crc(source,FRAME_BYTES/4);}
static void publish(unsigned frame){uint32_t d[DESC_WORDS]={0};d[1]=FRAME_BASE;d[2]=frame;assert(queue_publish(&queue,0,d));}
static void verify(unsigned codec){unsigned i,n=FRAME_BYTES/4;uint32_t*h=(uint32_t*)wire;
 assert(client && !active && !encoding && !waiting && !nr && wire_n==total);
 assert(h[0]==PROTO && h[3]>>8==codec && h[47]==tile_slot_crc[0] && h[68]==tile_header_crc(h,68));
 assert(h[4]==queue.head+1 && h[5]==FRAME_BASE && h[6]==queue_front(&queue)[2]);
 if(codec==2){memset(expected,0,packed_size(n));for(i=0;i<n;i++){
  expected[3*i]=(unsigned char)source[i];expected[3*i+1]=(unsigned char)(source[i]>>8);expected[3*i+2]=(unsigned char)(source[i]>>16);
  expected[3*n+i/8]|=(unsigned char)(((source[i]>>24)&1)<<(i%8));
 }assert(h[2]==packed_size(n));assert(!memcmp(wire+sizeof(header),expected,h[2]));}
 else {assert(codec==0 && h[2]==FRAME_BYTES);assert(!memcmp(wire+sizeof(header),source,FRAME_BYTES));}
 roundtrips++;
}
static void acknowledge(void){uint32_t q[4]={PROTO,2,queue.meta[M_BOOT],queue.head+1};struct pbuf p={16,q};wire_n=0;
 assert(received(0,&peer,&p,ERR_OK)==ERR_OK);finish();assert(queue.head==queue.tail && !queue.refs[0]);abort_client();
}
static void fresh(unsigned frame){fill(frame+126);publish(frame);connect_peer();}
static void boundaries(void){unsigned i;uint32_t d[40]={0},n=921600,last=0;PackedFailure f={0};
 for(i=0;i<=n;i+=17){uint32_t r=packed_stream_ready(276,n,i,0,0);assert(r==276+3*i && r>=last && r<=276+3*n);last=r;}
 assert(packed_stream_ready(276,n,n,0,0)==276+3*n);assert(packed_stream_ready(276,n,n,1,0)==276+packed_size(n));
 assert(!packed_stream_ready(276,n,n-1,1,0));assert(!packed_stream_ready(276,n,n+1,0,0));assert(!packed_stream_ready(276,n,n,1,1));
 assert(!packed_stream_ready(0xffffffffu,n,n,1,0));assert(!packed_stream_ready(0,0x40000000u,0,0,0));
 d[0]=0;d[1]=FRAME_BASE;d[2]=0xffffffffu;packed_failure_set(&f,0,d,1);assert(packed_failure_matches(&f,0,d,1));
 for(i=0;i<5;i++){uint32_t b=0,c=1,save;packed_failure_set(&f,0,d,1);save=i<3?d[i]:0;
  if(i<3)d[i]^=1;else if(i==3)b=1;else c=2;
  assert(!packed_failure_matches(&f,b,d,c) && !f.valid);if(i<3)d[i]=save;
  assert(!packed_failure_matches(&f,0,d,1));
 }
}
int main(void){unsigned s;source=VirtualAlloc((void*)(uintptr_t)FRAME_BASE,FRAME_STRIDE,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
 assert(source==(void*)(uintptr_t)FRAME_BASE);queue_init(&queue,metadata,descriptors,126);ready=1;boundaries();
 for(s=0;s<8;s++){scenario=s;fresh(s+1);request(14);finish();verify(2);acknowledge();}
 for(s=0;s<3;s++){unsigned cutoff=276+(s+1)*20000;fresh(20+s);request(14);
  while(offset<cutoff)poll_once();assert(encoding==2 || !packer.failed);assert(nr);abort_client();assert(queue.head!=queue.tail && queue.refs[0]);
  connect_peer();request(14);finish();verify(2);retries++;acknowledge();
 }
 for(s=0;s<2;s++){unsigned ix=s?800000:100;uint32_t original;fresh(30+s);original=source[ix];source[ix]|=0x02000000u;request(14);finish();
  assert(!client && !nr && packed_failure.valid && queue.refs[0]);if(s){assert(wire_n>sizeof(header));late_fail++;}else{assert(!wire_n);pre_header_fail++;}
  connect_peer();request(14);finish();verify(0);assert(tile_header_crc(source,FRAME_BYTES/4)!=tile_slot_crc[0]);abort_client();
  source[ix]=original;connect_peer();request(14);finish();verify(0);assert(tile_header_crc(source,FRAME_BYTES/4)==tile_slot_crc[0]);acknowledge();
  fresh(40+s);request(14);finish();verify(2);assert(!packed_failure.valid);acknowledge();
 }
 /* A reconnect can confirm previously saved evidence while an old partial
  * transmission still has GEM references. The next event reuses scratch. */
 fresh(77);request(14);while(offset<50000)poll_once();assert(nr);retain_after_abort=1;abort_client();assert(hardware_n);
 connect_peer();acknowledge();fresh(78);request(14);finish();verify(2);acknowledge();check_hardware();hardware_n=0;
 assert(overlap_seen>0 && health_calls==polls && hardware_checks>1000 && copied_payload_writes>1000 && !borrowed_payload_writes);
 printf("{\"passed\":true,\"roundtrips\":%u,\"midstream_retries\":%u,\"early_invalid_abort\":%u,\"late_invalid_abort\":%u,\"overlapped_writes\":%u,\"borrow_immutability_checks\":%u,\"gem_retained_reference_checks\":%u,\"copied_payload_writes\":%u,\"borrowed_payload_writes\":%u,\"polls\":%u,\"tcp_aborts\":%u}\n",roundtrips,retries,pre_header_fail,late_fail,overlap_seen,held_checks,hardware_checks,copied_payload_writes,borrowed_payload_writes,polls,aborts);
 VirtualFree(source,0,MEM_RELEASE);return 0;
}
'''
c=('#define EXPECT_OLD_DMA_LIFETIME 1\n' if old_dma else '')+c.replace('#include "network.c"','#include "'+network.as_posix()+'"')
(O/'network_harness.c').write_text(c)
gcc='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe'
p=subprocess.run([gcc,'-std=c11','-O2','-Wall','-Wextra','-I'+str(O),'-I'+str(S),str(O/'network_harness.c'),'-o',str(O/'network_harness.exe')],capture_output=True,text=True)
(O/'compile.log').write_text(p.stdout+p.stderr);p.check_returncode()
p=subprocess.run([str(O/'network_harness.exe')],capture_output=True,text=True,timeout=90)
(O/'run.log').write_text(p.stdout+p.stderr)
if old_dma:
 assert p.returncode==41 and 'COUNTEREXAMPLE GEM reference changed' in p.stderr,(p.returncode,p.stdout,p.stderr)
 result=dict(counterexample_reproduced=True,exit_code=p.returncode,message=p.stderr,network_sha256=hashlib.sha256(network.read_bytes()).hexdigest())
 (O/'dma_counterexample.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));raise SystemExit(0)
p.check_returncode();result=json.loads(p.stdout)
result['source_sha256']={n:hashlib.sha256((S/n).read_bytes()).hexdigest() for n in ['network.c','packed_stream.h','packed_pixels.h','event_queue.h']}
result['scope']='Actual firmware network.c; simulated TCP borrowing, random ERR_MEM, delayed ACK/window pressure and GEM references retained after abort. Not an Ethernet speed or physical DMA timing test.'
(O/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
