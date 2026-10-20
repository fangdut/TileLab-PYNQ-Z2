"""Compile actual service C against MMIO/lwIP mocks and test ownership faults."""
from pathlib import Path
import argparse,subprocess,json,hashlib
R=Path(__file__).resolve().parents[2]
STUB=r'''
#ifndef STUB_H
#define STUB_H
#include <stdint.h>
#include <string.h>
#include <stdio.h>
typedef int err_t;typedef uint16_t u16_t;typedef uintptr_t INTPTR;typedef uintptr_t UINTPTR;typedef uint64_t XTime;
#define ERR_OK 0
#define ERR_ABRT -1
#define TCP_MSS 1460
#define TCP_WRITE_FLAG_COPY 1
#define IP_ADDR_ANY 0
#define COUNTS_PER_SECOND 1000000u
struct tcp_pcb {int unused;};struct pbuf {unsigned tot_len;const unsigned char *payload;};
static struct tcp_pcb pcb;static uint64_t clock_now;static unsigned writes,aborts,ctrl;static uint32_t mmio[32];static unsigned char wire[4096];static unsigned wire_bytes;
static struct tcp_pcb *tcp_new(void){return &pcb;}
static int tcp_bind(struct tcp_pcb *p,int a,unsigned port){(void)p;(void)a;(void)port;return 0;}
static int tcp_close(struct tcp_pcb *p){(void)p;return 0;}
static struct tcp_pcb *tcp_listen(struct tcp_pcb *p){return p;}
#define tcp_accept(...) ((void)0)
#define tcp_err(...) ((void)0)
#define tcp_recv(...) ((void)0)
#define tcp_sent(...) ((void)0)
#define tcp_nagle_disable(...) ((void)0)
#define tcp_recved(...) ((void)0)
#define pbuf_free(...) ((void)0)
static void tcp_abort(struct tcp_pcb *p){(void)p;aborts++;}
static unsigned tcp_sndbuf(struct tcp_pcb *p){(void)p;return 65535;}
static int tcp_write(struct tcp_pcb *p,const void *data,unsigned n,int flags){(void)p;(void)flags;if(wire_bytes+n<=sizeof(wire)){memcpy(wire+wire_bytes,data,n);wire_bytes+=n;}return 0;}
static int tcp_output(struct tcp_pcb *p){(void)p;return 0;}
static unsigned pbuf_copy_partial(struct pbuf *p,void *dst,unsigned n,unsigned pos){memcpy(dst,p->payload+pos,n);return n;}
static void XTime_GetTime(XTime *t){*t=clock_now;}
static uint32_t Xil_In32(uint32_t addr){return addr==0x43c00100u?0x16700601u:ctrl;}
static void Xil_Out32(uint32_t addr,uint32_t value){writes++;mmio[(addr-0x43c10000u)/4]=value;}
#define Xil_DCacheFlushRange(...) ((void)0)
#define Xil_DCacheInvalidateRange(...) ((void)0)
#endif
'''
HARNESS=r'''
#define CHECK(x) do{checks++;if(!(x)){printf("FAIL line%d: %s\n",__LINE__,#x);return 1;}}while(0)
static unsigned checks;
static unsigned char zeros[32768];
static uint32_t header[16];
static void make_header(void){memset(header,0,sizeof(header));header[0]=MAGIC;header[1]=2;header[2]=123;header[3]=INPUT_BYTES;header[4]=crc(paired,INPUT_BYTES);header[5]=header[6]=header[7]=256;header[11]=18;header[12]=9;header[15]=crc(header,60);}
static err_t feed(const void *data,unsigned n){struct pbuf p={n,data};return receive(0,&pcb,&p,0);}
static void body_all(void){unsigned remaining=INPUT_BYTES;while(remaining){unsigned n=remaining>sizeof(zeros)?sizeof(zeros):remaining;feed(zeros,n);remaining-=n;}}
int main(void){
 CHECK(crc("123456789",9)==0xcbf43926u);CHECK(crc("",0)==0u);
 memset(paired,0,sizeof(paired));reference_service_start();make_header();
 CHECK(accept_one(0,&pcb,0)==0);header[15]^=1;CHECK(feed(header,64)==ERR_ABRT);CHECK(!peer && !writes);make_header();
 CHECK(accept_one(0,&pcb,0)==0);for(unsigned i=0;i<64;i++)CHECK(feed((unsigned char*)header+i,1)==0);CHECK(phase==1);feed(zeros,1000);CHECK(body==1000 && !running);abort_peer();CHECK(!running);
 CHECK(accept_one(0,&pcb,0)==0);header[4]^=1;header[15]=crc(header,60);feed(header,64);body_all();CHECK(phase==2);reference_service_poll();CHECK(!writes && !running && phase==3);CHECK(response[1]==2);abort_peer();make_header();
 CHECK(accept_one(0,&pcb,0)==0);feed(header,64);body_all();reference_service_poll();CHECK(running && phase==5);CHECK(writes==13);CHECK(mmio[0x28/4]==256 && mmio[0x58/4]==18 && mmio[0x60/4]==9);abort_peer();CHECK(running);CHECK(accept_one(0,&pcb,0)==ERR_ABRT);ctrl=2;reference_service_poll();CHECK(!running && !peer);ctrl=0;
 CHECK(accept_one(0,&pcb,0)==0);feed(header,64);body_all();reference_service_poll();CHECK(running);clock_now+=6000000;reference_service_poll();CHECK(response[1]==4 && running);unsigned sent_prefix=tx;reference_service_poll();CHECK(tx>=sent_prefix && response[1]==4);abort_peer();CHECK(running);ctrl=2;reference_service_poll();CHECK(!running);ctrl=0;
 CHECK(accept_one(0,&pcb,0)==0);feed(header,64);clock_now+=16000000;reference_service_poll();CHECK(!peer && !running);
 CHECK(accept_one(0,&pcb,0)==0);header[5]=0xffffffff;header[15]=crc(header,60);CHECK(feed(header,64)==ERR_ABRT && !peer);make_header();
 CHECK(accept_one(0,&pcb,0)==0);feed(header,64);body_all();CHECK(feed(zeros,1)==ERR_ABRT);CHECK(!peer && !running);
 CHECK(accept_one(0,&pcb,0)==0);header[1]=1;header[3]=0;header[15]=crc(header,60);feed(header,64);CHECK(response[1]==0 && response[3]==0 && response[15]==crc(response,60));
 printf("PASS: %u actual-C assertions; fragmented upload, CRC, bounds, disconnect/DMA ownership, timeout, ABI\n",checks);return 0;
}
'''
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--compiler',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'stub.h').write_text(STUB)
    for name in ('lwip/tcp.h','xil_io.h','xil_cache.h','xiltimer.h'):
        f=a.out/name;f.parent.mkdir(exist_ok=True);f.write_text('#include "stub.h"\n')
    source=R/'experimental/reference_v167/reference_service.c';fixture=a.out/'fixture.c';fixture.write_text('#include "'+source.as_posix()+'"\n'+HARNESS)
    exe=a.out/'test.exe';compile=subprocess.run([str(a.compiler),'-std=c11','-O2','-Wall','-Wextra','-I',str(a.out),str(fixture),'-o',str(exe)],capture_output=True,text=True);(a.out/'compiler.log').write_text(compile.stdout+compile.stderr)
    if compile.returncode:raise RuntimeError(compile.stderr)
    test=subprocess.run([str(exe)],capture_output=True,text=True);(a.out/'test.log').write_text(test.stdout+test.stderr);print(test.stdout,flush=True)
    if test.returncode:raise RuntimeError('Actual C service mock test failed')
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,scope='ACTUAL_C_MMIO_LWIP_MOCKS_NOT_BOARD',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),output=test.stdout),indent=2))
if __name__=='__main__':main()
