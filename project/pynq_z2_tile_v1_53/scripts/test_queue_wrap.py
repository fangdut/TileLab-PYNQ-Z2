"""Actual C vs independent Python deque; include old-code failing controls."""
from pathlib import Path
from collections import deque,Counter
import ctypes,subprocess,json,random,hashlib
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_16';O=R/'reports/v137/queue_wrap';O.mkdir(parents=True,exist_ok=True)
gcc='D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe';MASK=0xffffffff
src=r'''
#include "event_queue.h"
#ifndef META_WORDS
#define META_WORDS 64u
#define OLD_QUEUE 1
#endif
static EventQueue q;static uint32_t m[META_WORDS],d[QUEUE_CAPACITY*DESC_WORDS];
__declspec(dllexport) void seed(uint32_t n,unsigned pos){
 queue_init(&q,m,d,111);q.head=q.tail=q.last_ack=n;m[M_HEAD]=m[M_TAIL]=m[M_ACK]=n;
#ifndef OLD_QUEUE
 q.read_pos=q.write_pos=pos;m[M_QUEUE_READ_POS]=m[M_QUEUE_WRITE_POS]=pos;
#else
 (void)pos;
#endif
}
__declspec(dllexport) unsigned put(unsigned slot,uint32_t stamp){
 uint32_t w[DESC_WORDS]={0};w[1]=FRAME_BASE+slot*FRAME_STRIDE;w[2]=stamp;return queue_publish(&q,slot,w);
}
__declspec(dllexport) void ack(uint32_t n){m[M_ACK]=n;queue_ack(&q);}
__declspec(dllexport) void snapshot(uint32_t *out){
 unsigned i,r,w;
#ifdef OLD_QUEUE
 r=q.head%QUEUE_CAPACITY;w=q.tail%QUEUE_CAPACITY;
#else
 r=q.read_pos;w=q.write_pos;
#endif
 out[0]=q.head;out[1]=q.tail;out[2]=m[M_DEPTH];out[3]=r;out[4]=w;
 out[5]=(uint32_t)q.slot_used;out[6]=(uint32_t)(q.slot_used>>32);out[7]=m[M_ACK_ERRORS];out[8]=q.last_ack;
#ifndef OLD_QUEUE
 out[9]=m[M_QUEUE_READ_POS];out[10]=m[M_QUEUE_WRITE_POS];
#else
 out[9]=r;out[10]=w;
#endif
 for(i=0;i<FRAME_SLOTS;i++)out[16+i]=q.refs[i];
 for(i=0;i<DESC_WORDS;i++)out[64+i]=d[r*DESC_WORDS+i];
}
'''
(O/'wrapper.c').write_text(src)
def library(root,name):
 inc=root/(root.name+'.sdk')/'ethernet_sources'
 cmd=[gcc,'-std=c11','-O2','-Wall','-Wextra','-shared','-I'+str(inc),str(O/'wrapper.c'),'-o',str(O/(name+'.dll'))]
 p=subprocess.run(cmd,capture_output=True,text=True);(O/(name+'_compile.log')).write_text(p.stdout+p.stderr);p.check_returncode()
 lib=ctypes.CDLL(str(O/(name+'.dll')));lib.seed.argtypes=[ctypes.c_uint32,ctypes.c_uint];lib.put.argtypes=[ctypes.c_uint,ctypes.c_uint32];lib.put.restype=ctypes.c_uint;lib.ack.argtypes=[ctypes.c_uint32];lib.snapshot.argtypes=[ctypes.POINTER(ctypes.c_uint32)]
 return lib
buf=(ctypes.c_uint32*104)()
def snap(lib):lib.snapshot(buf);return list(buf)
old=library(B,'baseline');new=library(R,'candidate')
# FIFO corruption before the nominal capacity is reached.
old.seed(0xfffffffc,0)
for i in range(5):assert old.put(i,100+i)
s=snap(old);assert s[2]==5 and s[64]==1 and s[66]==104
baseline_overwrite=dict(depth=s[2],expected_event=0xfffffffd,observed_event=s[64],expected_stamp=100,observed_stamp=s[66])
old.seed(0xffffffff,3);assert old.put(4,77);old.ack(0);s=snap(old);assert s[0]==0xffffffff and s[2]==1
baseline_zero=dict(head=s[0],depth_after_ack_zero=s[2])
# Deterministic boundary controls on all physical start positions.
boundary=0
for pos in range(12):
 new.seed(0xfffffffc,pos)
 for i in range(12):assert new.put(i%4,100+i)
 assert not new.put(5,999)
 for i in range(12):
  s=snap(new);event=(0xfffffffd+i)&MASK
  assert s[64]==event and s[66]==100+i and s[65]==0x10100000+(i%4)*0x400000
  new.ack(event);before=snap(new);new.ack(event);assert snap(new)==before
  boundary+=1
 s=snap(new);assert s[2]==s[5]==s[6]==0 and sum(s[16:64])==0
random_checks=0;crossings=0
for base in (0,0xffffffe0,0xfffffff8,0xffffffff):
 for pos in range(12):
  rng=random.Random((base<<8)|pos);new.seed(base,pos);items=deque();head=tail=last=base;errors=0;rd=wr=pos
  for i in range(2500):
   if rng.random()<.62:
    slot=rng.randrange(48);stamp=i+1;allowed=len(items)<12
    assert bool(new.put(slot,stamp))==allowed
    if allowed:
     tail=(tail+1)&MASK;crossings+=tail==0;items.append((tail,slot,stamp));wr=(wr+1)%12
   else:
    chance=rng.random();a=((head+1)&MASK) if chance<.8 else last if chance<.9 else rng.getrandbits(32)
    new.ack(a)
    if a!=last:
     if items and a==((head+1)&MASK):items.popleft();head=(head+1)&MASK;rd=(rd+1)%12;last=a
     else:errors+=1;last=head
   s=snap(new);refs=Counter(v[1] for v in items);used=sum(1<<slot for slot in refs)
   assert s[:9]==[head,tail,len(items),rd,wr,used&MASK,used>>32,errors,last],(base,pos,i,s[:9])
   assert s[9:11]==[rd,wr] and s[16:64]==[refs[j] for j in range(48)]
   if items:
    event,slot,stamp=items[0];assert s[64:67]==[event,0x10100000+slot*0x400000,stamp],(base,pos,i)
   random_checks+=1
assert crossings>=36
result=dict(passed=True,baseline_failures_reproduced=dict(physical_slot_overwrite=baseline_overwrite,zero_ack_ignored=baseline_zero),boundary_events=boundary,random_operations=random_checks,sequence_crossings=crossings,all_physical_start_positions=12,
            candidate_header_sha256=hashlib.sha256((R/(R.name+'.sdk')/'ethernet_sources/event_queue.h').read_bytes()).hexdigest(),baseline_header_sha256=hashlib.sha256((B/(B.name+'.sdk')/'ethernet_sources/event_queue.h').read_bytes()).hexdigest(),scope='Actual native-compiled C queue with independent deque/refcounts; not ARM timing or actual board wrap yet')
(R/'reports/v137/queue_wrap_native.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
