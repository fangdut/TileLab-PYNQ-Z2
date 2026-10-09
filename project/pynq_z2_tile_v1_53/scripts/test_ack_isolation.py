"""Actual C queue versus independent FIFO: invalid ACKs never poison futures."""
from pathlib import Path
from collections import deque,Counter
import ast,ctypes,subprocess,json,random,hashlib
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_17';O=R/'reports/v132/ack_native';O.mkdir(parents=True,exist_ok=True)
tree=ast.parse((R/'scripts/test_queue_wrap.py').read_text());src=next(ast.literal_eval(v.value) for v in tree.body if isinstance(v,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='src' for t in v.targets))
src=src.replace('out[8]=q.last_ack;','out[8]=q.last_ack;out[11]=m[M_ACK];')
src+='\n__declspec(dllexport) void poll(void){queue_ack(&q);}\n__declspec(dllexport) void address(uint32_t a){queue_front(&q)[1]=a;}\n'
(O/'wrapper.c').write_text(src)
MASK=0xffffffff;buf=(ctypes.c_uint32*104)()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def library(root,name):
 cmd=['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/gcc.exe','-std=c11','-O2','-Wall','-Wextra','-shared','-I'+str(root/(root.name+'.sdk')/'ethernet_sources'),str(O/'wrapper.c'),'-o',str(O/(name+'.dll'))]
 p=subprocess.run(cmd,capture_output=True,text=True);(O/(name+'_compile.log')).write_text(p.stdout+p.stderr);p.check_returncode()
 q=ctypes.CDLL(str(O/(name+'.dll')));q.seed.argtypes=[ctypes.c_uint32,ctypes.c_uint];q.put.argtypes=[ctypes.c_uint,ctypes.c_uint32];q.put.restype=ctypes.c_uint;q.ack.argtypes=[ctypes.c_uint32];q.snapshot.argtypes=[ctypes.POINTER(ctypes.c_uint32)];q.address.argtypes=[ctypes.c_uint32]
 return q
def snap(q):q.snapshot(buf);return list(buf)
old=library(B,'baseline');q=library(R,'candidate');failures=[]
for base in (0,0xffffffff):
 old.seed(base,0);old.ack((base+1)&MASK);assert old.put(2,99);old.ack((base+1)&MASK);s=snap(old)
 assert s[0]==base and s[2]==1
 failures.append(dict(initial_head=base,rejected_future=(base+1)&MASK,head_after_later_valid_ack=s[0],depth=s[2]))
boundaries=0
for base in (0,1,123,0xfffffffc,0xfffffffe,0xffffffff):
 for pos in range(12):
  for wrong in ((base+1)&MASK,(base+6)&MASK,(base-1)&MASK):
   q.seed(base,pos);q.ack(wrong);s=snap(q)
   assert s[:5]==[base,base,0,pos,pos] and s[7:9]==[1,base] and s[11]==base
   for _ in range(10):q.poll();assert snap(q)==s
   assert q.put(47,55);published=snap(q)
   for _ in range(10):q.poll();assert snap(q)==published
   q.ack((base+1)&MASK);after=snap(q);assert after[0]==((base+1)&MASK) and after[2]==0 and not any(after[16:64])
   q.ack((base+1)&MASK);assert snap(q)==after;boundaries+=1
# Descriptor address corruption must not consume a valid slot or latch the ACK.
q.seed(0,0);assert q.put(47,77);good=0x10100000+47*0x400000;q.address(0)
q.ack(1);s=snap(q);assert s[0]==0 and s[2]==1 and s[7:9]==[1,0] and s[16+47]==1
for _ in range(10):q.poll();assert snap(q)==s
q.address(good);q.ack(1);s=snap(q);assert s[0]==1 and s[2]==0 and s[7]==1 and s[16+47]==0
operations=0;crossings=0
for base in (0,0xffffffe0,0xfffffff8,0xffffffff):
 for pos in range(12):
  rng=random.Random((base<<8)|pos);q.seed(base,pos);items=deque();head=tail=base;rd=wr=pos;errors=0
  for i in range(2500):
   choice=rng.random()
   if choice<.56:
    slot=rng.randrange(48);allowed=len(items)<12;assert bool(q.put(slot,i+1))==allowed
    if allowed:tail=(tail+1)&MASK;crossings+=tail==0;items.append((tail,slot,i+1));wr=(wr+1)%12
   elif choice<.95:
    a=((head+1)&MASK) if choice<.8 else head if choice<.85 else (head+2)&MASK if choice<.9 else rng.getrandbits(32)
    q.ack(a)
    if a!=head:
     if items and a==((head+1)&MASK):items.popleft();head=(head+1)&MASK;rd=(rd+1)%12
     else:errors+=1
   else:q.poll()
   s=snap(q);refs=Counter(v[1] for v in items);used=sum(1<<j for j in refs)
   assert s[:9]==[head,tail,len(items),rd,wr,used&MASK,used>>32,errors,head],(base,pos,i,s[:9])
   assert s[9:12]==[rd,wr,head] and s[16:64]==[refs[j] for j in range(48)]
   if items:
    event,slot,stamp=items[0];assert s[64:67]==[event,0x10100000+slot*0x400000,stamp]
   operations+=1
assert crossings>=36
result=dict(passed=True,baseline_failures=failures,boundary_scenarios=boundaries,random_operations=operations,sequence_crossings=crossings,physical_start_positions=12,invalid_slot_recovery=True,candidate_header_sha256=sha(R/(R.name+'.sdk')/'ethernet_sources/event_queue.h'),baseline_header_sha256=sha(B/(B.name+'.sdk')/'ethernet_sources/event_queue.h'),scope='Actual C with independent FIFO/refcounts; invalid mailbox is consumed and fresh future ACK remains possible; not ARM performance')
(R/'reports/v132/ack_isolation_native.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
