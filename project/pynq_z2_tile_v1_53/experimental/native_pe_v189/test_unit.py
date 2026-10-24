"""Independent scalar oracle, C model and native six-stage RTL with stalls/reset."""
from pathlib import Path
import argparse,random,hashlib,json,re,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--cases',type=int,default=2048);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent;out=a.out.resolve();rng=random.Random(189)
def signed(x,b):return x-(1<<b) if x&(1<<(b-1)) else x
fields={n:[] for n in ['mode','activation','centers0','centers1','query','expected']}
for i in range(a.cases):
 nearest=i%3==0;act=[rng.randrange(256) for _ in range(8)];c0=rng.getrandbits(1024);c1=rng.getrandbits(1024);q=rng.getrandbits(1024)
 if i<32:
  act=[(0,127,128,255)[i%4]]*8;c0=sum(((0,127,128,255)[(i//4)%4])<<(j*8) for j in range(128));c1=((1<<1024)-1)^c0
  q=sum((32768 if (j+i)%2 else 32767)<<(j*16) for j in range(64))
 expected=0
 for lane in range(16):
  lo=0;hi=0
  for j in range(8):
   if nearest:
    d=(lane%8)*8+j;center=((c0 if lane<8 else c1)>>((d%16)*64+(d//16)*16))&65535
    delta=signed((q>>(16*d))&65535,16)-signed(center,16);lo+=delta*delta
   else:
    av=signed(act[j],8);lo+=av*signed((c0>>(lane*64+j*8))&255,8);hi+=av*signed((c1>>(lane*64+j*8))&255,8)
  expected|=(lo&((1<<40)-1))<<(lane*40);expected|=(hi&((1<<20)-1))<<(640+lane*20)
 values=[int(nearest),sum(v<<(j*8) for j,v in enumerate(act)),c0,c1,q,expected]
 for name,value in zip(fields,values):fields[name].append(value)
for name,data in fields.items():(out/(name+'.mem')).write_text(''.join(f'{v:x}\n' for v in data))
rows=[' '.join(f'{fields[n][i]:x}' for n in fields) for i in range(a.cases)];(out/'vectors.txt').write_text('\n'.join(rows)+'\n')
runner=r'''#include "shared_mac_model.cpp"
#include <fstream>
#include <string>
#include <cstdio>
int main(){std::ifstream f("vectors.txt");std::string m,a,c0,c1,q,e;unsigned n=0;while(f>>m>>a>>c0>>c1>>q>>e){
auto result=shared_mac(m!="0",ap_uint<64>(a.c_str(),16),ap_uint<1024>(c0.c_str(),16),ap_uint<1024>(c1.c_str(),16),ap_uint<1024>(q.c_str(),16));
if(result!=ap_uint<960>(e.c_str(),16)){printf("C_MODEL_FAIL %u\n",n);return 2;}n++;}printf("NATIVE_SHARED_MAC_C_MODEL_PASS cases=%u\n",n);}
'''
(out/'runner.cpp').write_text(runner);(out/'shared_mac_model.cpp').write_bytes((root/'shared_mac_model.cpp').read_bytes())
with (out/'compile.log').open('w') as log:subprocess.run(['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O2','-std=c++17','-static','-I','D:/2025.2/Vitis/include',str(out/'runner.cpp'),'-o',str(out/'check.exe')],stdout=log,stderr=subprocess.STDOUT,check=True)
r=subprocess.run([str(out/'check.exe')],cwd=out,capture_output=True,text=True,check=True);(out/'c_model.log').write_text(r.stdout);assert f'cases={a.cases}' in r.stdout
tb=r'''`timescale 1ns/1ps
module tb_native_mac;
reg clk=0,rst=1,ce=0,nearest=0,valid_in=0;reg[63:0] act=0;reg[1023:0] c0=0,c1=0,q=0;wire[959:0] result;
always #5 clk=~clk;
shared_mac dut(.ap_clk(clk),.ap_rst(rst),.ap_ce(ce),.nearest(nearest),.activations(act),.centers0(c0),.centers1(c1),.query_bits(q),.ap_return(result));
reg modes[0:N-1];reg[63:0] acts[0:N-1];reg[1023:0] centers0[0:N-1],centers1[0:N-1],queries[0:N-1];reg[959:0] expecteds[0:N-1],pipe[0:5],reference_in;
reg[5:0] valid_pipe=0;integer checked=0,issued=0,flushed=0,stalled=0,reset_count=0,index=0,cycle=0,j,flush_add;
always @(posedge clk)begin
 if(rst)begin flush_add=0;for(j=0;j<5;j=j+1)flush_add=flush_add+valid_pipe[j];flushed=flushed+flush_add;valid_pipe<=0;reset_count=reset_count+1;end
 else if(ce)begin
  valid_pipe<={valid_pipe[4:0],valid_in};pipe[0]<=reference_in;for(j=1;j<6;j=j+1)pipe[j]<=pipe[j-1];if(valid_in)issued=issued+1;
 end else stalled=stalled+1;
 #1;
 if(!rst&&ce&&valid_pipe[5])begin if(result!==pipe[5])$fatal(1,"NATIVE_SHARED_MAC_RTL_MISMATCH checked=%0d got=%h expected=%h",checked,result,pipe[5]);checked=checked+1;end
end
initial begin
 $readmemh("mode.mem",modes);$readmemh("activation.mem",acts);$readmemh("centers0.mem",centers0);$readmemh("centers1.mem",centers1);$readmemh("query.mem",queries);$readmemh("expected.mem",expecteds);
 repeat(5)@(negedge clk);
 while(index<N)begin
  @(negedge clk);cycle=cycle+1;rst=(cycle%251==0);ce=(cycle%7!=0)&&(cycle%11!=0);valid_in=!rst&&ce;
  if(valid_in)begin nearest=modes[index];act=acts[index];c0=centers0[index];c1=centers1[index];q=queries[index];reference_in=expecteds[index];index=index+1;end
 end
 @(negedge clk);valid_in=0;rst=0;ce=1;repeat(10)@(negedge clk);
 if(issued!=N||checked+flushed!=issued||stalled==0||flushed==0)$fatal(1,"NATIVE_SHARED_MAC_RTL_COVERAGE issued=%0d checked=%0d flushed=%0d",issued,checked,flushed);
 $display("NATIVE_SHARED_MAC_RTL_PASS checked=%0d issued=%0d flushed=%0d stalled=%0d reset_cycles=%0d",checked,issued,flushed,stalled,reset_count);$finish;
end
initial begin #1000000;$fatal(1,"NATIVE_SHARED_MAC_RTL_TIMEOUT");end
endmodule
'''.replace('N-1',str(a.cases-1)).replace('index<N',f'index<{a.cases}').replace('issued!=N',f'issued!={a.cases}')
(out/'tb_native_mac.sv').write_text(tb)
started=time.monotonic()
for tool,args in [('xvlog',['-sv',str(root/'shared_mac.v'),str(out/'tb_native_mac.sv')]),('xelab',['tb_native_mac','-s','native_mac_test','-debug','off']),('xsim',['native_mac_test','-runall'])]:
 with (out/(tool+'.log')).open('w') as log:subprocess.run(['D:/2025.2/Vivado/bin/'+tool+'.bat',*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
log=(out/'xsim.log').read_text(errors='replace');m=re.search(r'NATIVE_SHARED_MAC_RTL_PASS checked=(\d+) issued=(\d+) flushed=(\d+) stalled=(\d+) reset_cycles=(\d+)',log)
if not m or 'Fatal:' in log or 'Error:' in log:raise RuntimeError('Native shared MAC did not pass')
j=dict(scope='NATIVE_SHARED_MAC_UNIT_C_AND_RTL_NOT_DETECTOR_OR_BOARD',passed=True,checked=int(m[1]),issued=int(m[2]),reset_flushed=int(m[3]),stalled=int(m[4]),reset_cycles=int(m[5]),source_sha256=hashlib.sha256((root/'shared_mac.v').read_bytes()).hexdigest(),c_model_sha256=hashlib.sha256((root/'shared_mac_model.cpp').read_bytes()).hexdigest(),enabled_clock_latency=6,scalar_oracle='Independent Python signed integers; lower16 partial sums and upper16 partial sums or exact squared differences',elapsed_seconds=time.monotonic()-started)
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
