"""Compile actual V1.42 firmware C: gate/recipe, protocol, CRC and prefix ABI.

MMIO and lwIP are host stubs. No Vitis build, ARM execution, JTAG or board
access occurs. Host C checks complement, but never replace, RTL/board tests.
"""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/(ROOT.name+'.sdk')/'ethernet_sources'
OUT = ROOT/'reports/v142/product_gate_native'
GCC = 'D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe'


def literal(path, name):
    """Reuse only a literal stub declaration, never execute historical scripts."""
    for statement in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(statement,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in statement.targets):
            return ast.literal_eval(statement.value)
    raise AssertionError(name)


MAIN = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define main firmware_main
#include "main.c"
#undef main
static unsigned checks, writes, last_cfg, recipes, corruptions, magic_rejections;
#define CHECK(x) do { checks++; if(!(x)){fprintf(stderr,"CHECK failed line %d: %s\n",__LINE__,#x);exit(1);} }while(0)
unsigned Xil_In32(unsigned a){(void)a;return 0;}
void Xil_Out32(unsigned a,unsigned b){writes++;if(a==0x41200008u)last_cfg=b;}
void Xil_DCacheDisable(void){} int xil_printf(const char*f,...){(void)f;return 0;}
void XTime_GetTime(XTime*t){*t=0;} void tile_network_start(void){} void tile_network_poll(void){}
static uint32_t m[META_WORDS+2], d[QUEUE_CAPACITY*DESC_WORDS];
static void reset(void){
 memset(m,0xa5,sizeof(m));queue_init(&queue,m,d,137);
 CHECK(m[META_WORDS]==0xa5a5a5a5u && m[META_WORDS+1]==0xa5a5a5a5u);
 CHECK(m[M_VERSION]==0x12a00u && m[M_PRODUCT_GATE_REQUEST]==0 && m[M_PRODUCT_GATE_APPLIED]==0);
 threshold=commit=writes=last_cfg=last_seq=0;best_slot=-1;dma_used=0;
 memset(tile_slot_crc,0,sizeof(tile_slot_crc));memset(&dma_recovery,0,sizeof(dma_recovery));
}
int main(void){
 unsigned gate,mode,t,previous,old,i;
 CHECK(META_WORDS==88 && M_PRODUCT_GATE_REQUEST==86 && M_PRODUCT_GATE_APPLIED==87);
 CHECK(M_RECOVERY_BASE+14==M_PRODUCT_GATE_REQUEST && M_HEALTH_BASE==66);
 CHECK(M_QUEUE_READ_POS==64 && M_QUEUE_WRITE_POS==65 && M_DETECT_MODE_REQUEST==61 && M_DETECT_MODE_APPLIED==62);
 CHECK(M_MAGIC==0 && M_VERSION==1 && M_BOOT==2 && M_CONFIG==21 && M_ACK_ERRORS==23 && DESC_WORDS==40);
 reset();
 for(gate=0;gate<2;gate++)for(mode=0;mode<3;mode++)for(t=1;t<=255;t++){
  m[M_THRESHOLD]=t;m[M_DETECT_MODE_REQUEST]=mode;m[M_PRODUCT_GATE_REQUEST]=gate;
  m[42]=17;m[43]=1;previous=writes;old=m[M_CONFIG];apply_recipe_if_idle();
  CHECK(writes==previous && m[M_CONFIG]==old);
  m[43]=0;apply_recipe_if_idle();CHECK(writes==previous && m[M_CONFIG]==old);
  m[43]=4;apply_recipe_if_idle();
  CHECK(writes==previous+3 && ((last_cfg>>8)&255)==t && m[M_CONFIG]==last_cfg);
  CHECK(m[M_DETECT_MODE_APPLIED]==mode && m[M_PRODUCT_GATE_APPLIED]==gate);
  CHECK(((last_cfg>>24)&3)==(mode==0?1:mode==1?0:3));
  CHECK(((last_cfg>>26)&1)==gate && ((last_cfg^old)>>31)==1);
  CHECK((last_cfg&0x78ffffffu)==(0x00f30007u|(t<<8)));
  previous=writes;apply_recipe_if_idle();CHECK(writes==previous);recipes++;
 }
 m[42]=0;m[43]=0;m[M_THRESHOLD]=90;m[M_DETECT_MODE_REQUEST]=2;m[M_PRODUCT_GATE_REQUEST]=0;
 apply_recipe_if_idle();CHECK(threshold==90 && m[M_PRODUCT_GATE_APPLIED]==0);
 // Change only the product gate, preserving requested detector parameters.
 previous=writes;m[42]=17;m[43]=1;m[M_PRODUCT_GATE_REQUEST]=1;
 apply_recipe_if_idle();CHECK(writes==previous && !(last_cfg&(1u<<26)));
 m[43]=4;apply_recipe_if_idle();CHECK(writes==previous+3 && (last_cfg&(1u<<26)));
 CHECK(((last_cfg>>8)&255)==90 && ((last_cfg>>24)&3)==3);
 previous=writes;m[42]=0;m[43]=0;m[M_PRODUCT_GATE_REQUEST]=0;
 apply_recipe_if_idle();CHECK(writes==previous+3 && !(last_cfg&(1u<<26)));
 previous=writes;
 {unsigned invalid_gate[]={2,3,255,0xffffffffu};
  for(i=0;i<4;i++){m[M_PRODUCT_GATE_REQUEST]=invalid_gate[i];m[M_THRESHOLD]=91;apply_recipe_if_idle();CHECK(writes==previous);}}
 m[M_PRODUCT_GATE_REQUEST]=0;
 {unsigned invalid_mode[]={3,4,255,0xffffffffu};
  for(i=0;i<4;i++){m[M_DETECT_MODE_REQUEST]=invalid_mode[i];apply_recipe_if_idle();CHECK(writes==previous);}}
 m[M_DETECT_MODE_REQUEST]=0;
 {unsigned invalid_threshold[]={0,256,0xffffffffu};
  for(i=0;i<3;i++){m[M_THRESHOLD]=invalid_threshold[i];apply_recipe_if_idle();CHECK(writes==previous);}}
 // Both gate settings are bound into the PL trailer CRC, before any slot or
 // best-frame decision is accepted. A valid CRC cannot upgrade old hardware.
 for(gate=0;gate<2;gate++){
  uint32_t good[40]={0},bad[40];unsigned word,bit;
  reset();good[0]=0x54465337u;good[1]=0x13572468u;good[2]=10;
  good[6]=4;good[7]=0x03f35a07u|(gate<<26);good[35]=FRAME_BYTES;
  good[37]=17;good[38]=1|2|8|16;good[8]=tile_descriptor_crc(good);
  consume(40,good,1000);CHECK(m[M_CAPTURED]==1 && m[M_DESC_VERIFIED]==1 && best_slot==40);
  CHECK(best[7]==good[7] && tile_slot_crc[40]==good[1]);
  memcpy(bad,good,sizeof(bad));bad[0]=0x54465336u;bad[8]=tile_descriptor_crc(bad);
  consume(41,bad,1001);magic_rejections++;
  CHECK(m[M_INVALID]==1 && m[M_DESC_CRC_ERRORS]==0 && m[M_CAPTURED]==1 && best_slot==40 && tile_slot_crc[41]==0);
  for(word=0;word<40;word++)for(bit=0;bit<32;bit++){
   memcpy(bad,good,sizeof(bad));bad[word]^=1u<<bit;consume(41,bad,1002);
   CHECK(m[M_CAPTURED]==1 && m[M_DESC_VERIFIED]==1 && best_slot==40);
   CHECK(tile_slot_crc[41]==0 && queue.tail==0 && m[42]==17 && last_seq==10);
   corruptions++;
  }
  CHECK(m[M_INVALID]==1281 && m[M_DESC_CRC_ERRORS]==1248);
  memcpy(bad,good,sizeof(bad));bad[2]=11;bad[38]=1|8|16;bad[8]=tile_descriptor_crc(bad);
  consume(41,bad,1003);CHECK(m[M_CAPTURED]==2 && m[M_DESC_VERIFIED]==2 && best_slot==41);
 }
 printf("{\"passed\":true,\"checks\":%u,\"recipe_combinations\":%u,\"invalid_recipe_inputs\":11,\"single_bit_corruptions\":%u,\"old_magic_valid_crc_rejected\":%u,\"new_magic_valid_frames\":4,\"prefix_abi_words\":86,\"meta_words\":88}\n",checks,recipes,corruptions,magic_rejections);
 return 0;
}
'''

NETWORK = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "network.c"
EventQueue queue;
uint32_t tile_slot_crc[FRAME_SLOTS];
static unsigned checks,cases,valid_capture,valid_config,invalid_requests,aborts;
#define CHECK(x) do { checks++; if(!(x)){fprintf(stderr,"CHECK failed line %d: %s\n",__LINE__,#x);exit(1);} }while(0)
void tile_capture_health(uint64_t t){(void)t;}
int tile_network_maintenance_safe(void){return 1;}
err_t tcp_write(struct tcp_pcb*p,const void*d,u16_t n,u8_t f){(void)p;(void)d;(void)n;(void)f;CHECK(0);return ERR_MEM;}
err_t tcp_output(struct tcp_pcb*p){(void)p;CHECK(0);return ERR_MEM;}
void tcp_abort(struct tcp_pcb*p){(void)p;aborts++;}
static uint32_t m[META_WORDS+2], d[QUEUE_CAPACITY*DESC_WORDS];
static struct tcp_pcb peer;
static int listed(unsigned flag,const unsigned *allowed,unsigned size){unsigned i;for(i=0;i<size;i++)if(flag==allowed[i])return 1;return 0;}
static void one(unsigned op,unsigned threshold_arg,unsigned flag,unsigned retained){
 unsigned allowed_capture[]={0,1,2,3,4,6,10,11,14,16,17,18,19,20,22,26,27,30};
 unsigned allowed_config[]={0,1,4,16,17,20};
 uint32_t before[META_WORDS],before_desc[QUEUE_CAPACITY*DESC_WORDS],packet[4]={PROTO,op,threshold_arg,flag},front[40]={0};
 unsigned valid_t=threshold_arg==1 || threshold_arg==90 || threshold_arg==255;
 unsigned valid=valid_t && (op==1?listed(flag,allowed_capture,18):op==5?listed(flag,allowed_config,6):0);
 memset(m,0xa5,sizeof(m));queue_init(&queue,m,d,137);
 CHECK(m[META_WORDS]==0xa5a5a5a5u && m[META_WORDS+1]==0xa5a5a5a5u);
 m[M_THRESHOLD]=66;m[M_DETECT_MODE_REQUEST]=1;m[M_PRODUCT_GATE_REQUEST]=1;
 if(retained){front[1]=FRAME_BASE;front[2]=99;CHECK(queue_publish(&queue,0,front));}
 memcpy(before,m,sizeof(before));memcpy(before_desc,d,sizeof(d));
 memset(&peer,0,sizeof(peer));client=&peer;active=waiting=encoding=rx_used=send_ready=0;
 want_rle=want_packed=reply_codec=0;memset(header,0,sizeof(header));
 {struct pbuf p={16,packet};CHECK(received(0,&peer,&p,ERR_OK)==ERR_OK);}
 CHECK(client==&peer && !aborts && rx_used==0);
 CHECK(m[M_PRODUCT_GATE_APPLIED]==0 && m[M_DETECT_MODE_APPLIED]==0 && m[M_CONFIG]==0);
 CHECK(!memcmp(d,before_desc,sizeof(d)) && queue.head==0 && queue.tail==retained);
 CHECK(m[M_ACK]==before[M_ACK] && m[M_ACK_ERRORS]==before[M_ACK_ERRORS]);
 if(valid){
  CHECK(m[M_THRESHOLD]==threshold_arg && m[M_PRODUCT_GATE_REQUEST]==((flag>>4)&1));
  CHECK(m[M_DETECT_MODE_REQUEST]==((flag&4)?2:(flag&1)) && m[M_ENABLE]==1);
  if(op==1){
   valid_capture++;CHECK(waiting==1 && active==0);
   CHECK(want_rle==((flag>>1)&1) && want_packed==((flag>>3)&1));
   CHECK(m[M_REQUEST]==(retained?0:1) && m[M_REASON]==(retained?0:2));
  }else{
   valid_config++;CHECK(waiting==0 && active==1 && header[1]==1 && header[2]==0);
   CHECK(m[M_REQUEST]==0 && m[M_REASON]==0);
  }
 }else{
  invalid_requests++;CHECK(!memcmp(m,before,sizeof(before)));
  CHECK(waiting==0 && active==1 && header[1]==2 && header[2]==0);
 }
 if(active){CHECK(header[3]==5 && sizeof(header)==276 && header[68]==tile_header_crc(header,68));}
 CHECK(m[META_WORDS]==0xa5a5a5a5u && m[META_WORDS+1]==0xa5a5a5a5u);
 cases++;
}
int main(void){
 unsigned op,flag,t,retained,thresholds[]={0,1,90,255,256,0xffffffffu};
 for(op=1;op<=5;op+=4)for(flag=0;flag<64;flag++)for(t=0;t<6;t++)for(retained=0;retained<2;retained++)one(op,thresholds[t],flag,retained);
 for(op=1;op<=5;op+=4)for(retained=0;retained<2;retained++){
  one(op,90,0x80000000u,retained);one(op,90,0xffffffffu,retained);
 }
 one(77,90,16,0);
 CHECK(valid_capture==108 && valid_config==36 && cases==1545 && invalid_requests==1401);
 // Split reception keeps the new orthogonal flag intact without applying a
 // partial command. This exercises the actual request reassembly path.
 {uint32_t packet[]={PROTO,5,90,20};struct pbuf first={3,packet},second={13,(unsigned char*)packet+3};
  queue_init(&queue,m,d,137);client=&peer;active=waiting=encoding=rx_used=0;
  CHECK(received(0,&peer,&first,ERR_OK)==ERR_OK && rx_used==3 && m[M_PRODUCT_GATE_REQUEST]==0);
  CHECK(received(0,&peer,&second,ERR_OK)==ERR_OK && rx_used==0 && m[M_PRODUCT_GATE_REQUEST]==1 && m[M_DETECT_MODE_REQUEST]==2);
  CHECK(m[M_PRODUCT_GATE_APPLIED]==0 && header[68]==tile_header_crc(header,68));
 }
 printf("{\"passed\":true,\"checks\":%u,\"request_cases\":%u,\"valid_capture_requests\":%u,\"valid_configure_requests\":%u,\"rejected_requests\":%u,\"split_request_cases\":1,\"response_header_bytes\":276}\n",checks,cases,valid_capture,valid_config,invalid_requests);
 return 0;
}
'''


def compile_case(name, code, stub, headers):
    directory = OUT/name
    directory.mkdir(parents=True,exist_ok=True)
    (directory/'stub.h').write_text(stub,encoding='utf-8')
    for header in headers:
        path=directory/header
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('#include "stub.h"\n',encoding='utf-8')
    (directory/'test.c').write_text(code,encoding='utf-8')
    command=[GCC,'-std=c11','-O2','-Wno-int-to-pointer-cast','-I'+str(directory),'-I'+str(SOURCE),
             str(directory/'test.c'),'-o',str(directory/'test.exe')]
    compiled=subprocess.run(command,capture_output=True,text=True,timeout=60)
    (directory/'compile.log').write_text(compiled.stdout+compiled.stderr,encoding='utf-8')
    compiled.check_returncode()
    tested=subprocess.run([str(directory/'test.exe')],capture_output=True,text=True,timeout=30)
    (directory/'result.log').write_text(tested.stdout+tested.stderr,encoding='utf-8')
    tested.check_returncode()
    result=json.loads(tested.stdout)
    result['harness_sha256']=hashlib.sha256(code.encode()).hexdigest()
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    main_stub=literal(ROOT/'scripts/test_detection_mode_native.py','stub')
    network_stub=literal(ROOT/'scripts/test_packed_stream_native.py','stub')
    results={
        'application':compile_case('application',MAIN,main_stub,('xil_io.h','xil_cache.h','xil_printf.h','xiltimer.h')),
        'protocol':compile_case('protocol',NETWORK,network_stub,
            ('lwip/init.h','lwip/tcp.h','lwip/dhcp.h','lwip/etharp.h','lwip/ip4_frag.h','netif/xadapter.h',
             'xiltimer.h','xil_exception.h','xil_cache.h','xil_mmu.h','xil_printf.h'))}
    result=dict(passed=all(v['passed'] for v in results.values()),
        scope='Compiled actual main.c/network.c/event_queue.h with native MMIO/lwIP stubs. No ARM, FPGA, DMA timing, actual network or board operation.',
        checks=sum(v['checks'] for v in results.values()), results=results,
        source_sha256={name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()
                       for name in ('main.c','network.c','event_queue.h','descriptor_crc.h')},
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write=OUT/'summary.json'
    write.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
