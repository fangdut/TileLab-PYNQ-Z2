"""Compile actual C predicates/config/profile reply with local MMIO stubs.

This proves arithmetic and write guards, not lwIP/interrupt/physical board behavior.
Requires a C compiler; emits new evidence only, never programs hardware.
"""
from pathlib import Path
import argparse,ctypes,hashlib,json,os,subprocess
ROOT=Path(__file__).resolve().parents[1]

def predicate(text,marker):
    i=text.index(marker);j=text.index('{',i);condition=text[text.index('(',i)+1:j].strip()
    if not condition.endswith(')'):raise ValueError('Cannot extract actual C condition')
    return condition[:-1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--compiler',required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    f=ROOT/'pynq_z2_tile_v1_53.sdk/ethernet_sources';network=(f/'network.c').read_text();main=(f/'main.c').read_text()
    config=main[main.index('static void config(unsigned t)'):main.index('static unsigned free_slot(void)')]
    reply_body=network[network.index('uint32_t lo=Xil_In32',network.index('else if(rx[1]==6)')):network.index('reply(1,0);',network.index('else if(rx[1]==6)'))]
    guard=predicate(network,'if((rx[1]==1u');capture=predicate(network,'if(rx[1]==1 &&');configure=predicate(network,'if(rx[1]==5 &&')
    source='''#include <stdint.h>
#include "event_queue.h"
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif
static uint32_t meta[128],desc[QUEUE_CAPACITY*DESC_WORDS+1],fake_model,last_config,roi_min,roi_max,header[69];
static unsigned threshold=0,commit=0;
EventQueue queue;
static uint32_t Xil_In32(uint32_t addr){return addr==0x43c00100u?fake_model:addr==0x41210000u?roi_min:addr==0x41210008u?roi_max:0u;}
static void Xil_Out32(uint32_t addr,uint32_t value){if(addr==0x41200008u)last_config=value;else if(addr==0x41210000u)roi_min=value;else if(addr==0x41210008u)roi_max=value;}
'''+config+f'''
EXPORT unsigned allowed(unsigned op,unsigned t,unsigned flags,unsigned identity){{
 uint32_t rx[4]={{0,op,t,flags}};queue.meta=meta;meta[M_PL_MODEL]=identity;
 return !({guard}) && (({capture}) || ({configure}));
}}
EXPORT unsigned apply_config(unsigned identity){{
 unsigned i;for(i=0;i<128;i++)meta[i]=0xabc00000u+i;desc[QUEUE_CAPACITY*DESC_WORDS]=0xcafefaceu;
 queue_init(&queue,meta,desc,123);fake_model=identity;config(90);return last_config;
}}
EXPORT unsigned profile_word(unsigned which,unsigned bad_roi,unsigned identity){{
 queue.meta=meta;meta[M_PL_MODEL]=identity;roi_min=TILE_SINGLE_ROI_MIN+bad_roi;roi_max=TILE_SINGLE_ROI_MAX;
 {reply_body}
 return header[4+which];
}}
EXPORT unsigned get_meta(unsigned i){{return i<128?meta[i]:0;}}
EXPORT unsigned get_roi(unsigned i){{return i?roi_max:roi_min;}}
EXPORT unsigned canary(void){{return desc[QUEUE_CAPACITY*DESC_WORDS];}}
'''
    path=a.out/'fixture.c';path.write_text(source);library=a.out/('fixture.dll' if os.name=='nt' else 'fixture.so')
    args=[a.compiler,'-O2','-std=c11','-shared']+(['-static-libgcc'] if os.name=='nt' else ['-fPIC'])+['-I',str(f),str(path),'-o',str(library)]
    result=subprocess.run(args,capture_output=True,text=True);(a.out/'compiler.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stderr)
    lib=ctypes.CDLL(str(library.resolve()));u=ctypes.c_uint
    for name,count in [('allowed',4),('apply_config',1),('profile_word',3),('get_meta',1),('get_roi',1),('canary',0)]:getattr(lib,name).argtypes=[u]*count;getattr(lib,name).restype=u
    p=json.loads((ROOT/'config/single_tile.json').read_text());identity=p['model_id'];count=0
    for op in (1,5):
        for threshold in (0,1,89,90,91,255,256):
            for flags in range(1024):
                for model in (0,identity):
                    good=threshold==90 and model==identity and flags in ([612,614,622] if op==1 else [612])
                    assert bool(lib.allowed(op,threshold,flags,model))==good,(op,threshold,flags,model);count+=1
    assert lib.apply_config(identity)&0x7fffffff==0x7bf35a07
    assert lib.get_meta(1)==0x13200 and lib.get_meta(16)==0
    assert lib.get_roi(0)==(110<<16)|390 and lib.get_roi(1)==(609<<16)|889
    assert lib.canary()==0xcafeface
    expected=[p['profile_id'],(110<<16)|390,(609<<16)|889,identity,500,0x13200,1]
    assert [lib.profile_word(i,0,identity) for i in range(7)]==expected
    assert lib.profile_word(6,1,identity)==0 and lib.profile_word(6,0,0)==0
    proof=dict(actual_c_source_fragments=True,scope='Native C MMIO-stub check; not full firmware execution or board acceptance',predicate_checks=count,roi_config_and_profile_reply=True,all_exact=True,firmware_version=0x13200,profile_id=p['profile_id'],source_sha256={name:hashlib.sha256((f/name).read_bytes()).hexdigest() for name in ('main.c','network.c','event_queue.h','model_identity_v156.h','single_tile_profile.h')},fixture_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (a.out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof),flush=True)

if __name__=='__main__':main()
