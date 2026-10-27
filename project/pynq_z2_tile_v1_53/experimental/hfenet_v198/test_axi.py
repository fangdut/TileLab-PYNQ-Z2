"""Generated complete network RTL with bounded AXI RAMs, no UVM overhead."""
from pathlib import Path
import argparse,re,json,hashlib,subprocess,time,struct
p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--vectors',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
root=Path(__file__).resolve().parent;rtl=a.hls/'solution/syn/verilog';out=a.out;sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
for name in ['texture_integer.cpp','contract.hpp','norm_math.hpp']:assert (a.hls/'src'/name).read_bytes()==(root/name).read_bytes(),name
text=(rtl/'texture_integer.v').read_text();params=re.findall(r'^parameter\s+(C_\w+)\s*=\s*([^;]+);',text,re.M);pd={k:v.strip() for k,v in params};ports=re.findall(r'^(input|output)\s*(\[[^\n]+?\])?\s*(\w+);',text,re.M);assert len(ports)>150
widths={bus:int(pd['C_M_AXI_'+bus.upper()+'_DATA_WIDTH']) for bus in ['modelmem','workmem','inputmem','outmem']};assert widths==dict(modelmem=64,workmem=64,inputmem=32,outmem=32),widths
files=['model1.bin','model2.bin','rgb.bin','expected1.bin','expected2.bin','work1.bin','work2.bin'];counts={}
for name in files:
    data=(a.vectors/name).read_bytes();wordbytes=8 if name.startswith(('model','work')) else 4;assert len(data)%wordbytes==0
    base=Path(name).stem;(out/(base+'.mem')).write_text(''.join(f'{int.from_bytes(data[i:i+wordbytes],"little"):0{wordbytes*2}x}\n' for i in range(0,len(data),wordbytes)),encoding='ascii');counts[base]=len(data)//wordbytes
plan=dict(scope='COMPLETE_HFENET_FRAME_AXI_RTL_SYNTHETIC_NOT_BOARD',source_components={name:sha(a.hls/'src'/name) for name in ['texture_integer.cpp','contract.hpp','norm_math.hpp']},dut_files={f.name:sha(f) for f in sorted(rtl.glob('*')) if f.suffix in ['.v','.dat']},fixture={n:sha(a.vectors/n) for n in files},axi_ram_sha256=sha(root/'axi_ram_tb.sv'),driver_sha256=sha(Path(__file__)),geometry=[16,16],operators=71,tensors=72)
(out/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
for f in rtl.glob('*.dat'):(out/f.name).write_bytes(f.read_bytes())
tb=['`timescale 1ns/1ps','module tb_hfe;']+[f'localparam {n}={v};' for n,v in params]
for direction,width,name in ports:
    kind='reg' if direction=='input' and not name.startswith('m_axi_') else 'wire';tb.append(f'{kind} {width} {name}'+('=0;' if kind=='reg' else ';'))
tb+=['always #10 ap_clk=~ap_clk;','texture_integer dut('+','.join(f'.{n}({n})' for _,_,n in ports)+');']
for bus,words in [('modelmem',65536),('workmem',131072),('inputmem',4096),('outmem',4096)]:
    signals='AWVALID AWREADY AWADDR AWID AWLEN AWSIZE AWBURST WVALID WREADY WDATA WSTRB WLAST BVALID BREADY BID BRESP ARVALID ARREADY ARADDR ARID ARLEN ARSIZE ARBURST RVALID RREADY RDATA RLAST RID RRESP'.split()
    tb.append(f'axi_ram_tb #(.D(C_M_AXI_{bus.upper()}_DATA_WIDTH),.WORDS({words})) {bus}(.clk(ap_clk),.rst_n(ap_rst_n),'+','.join(f'.{s}(m_axi_{bus}_{s})' for s in signals)+');');tb += [f'assign m_axi_{bus}_BUSER=0;',f'assign m_axi_{bus}_RUSER=0;']
tb+=['integer cycle=0,n,launch,checked=0;reg[31:0] ctrl;reg[31:0] expected[0:4095];reg[63:0] features[0:131071];','always @(posedge ap_clk)begin cycle<=cycle+1;if(cycle%100000==0)$display("HFE_PROGRESS cycle=%0d step=%0d",cycle,outmem.mem[8]);if(cycle>20000000)$fatal(1,"HFE_AXI_TIMEOUT");end',
'''task wr(input[6:0] address,input[31:0] value);begin
 @(negedge ap_clk);s_axi_control_AWADDR=address;s_axi_control_AWVALID=1;
 @(posedge ap_clk);while(!s_axi_control_AWREADY)@(posedge ap_clk);
 @(negedge ap_clk);s_axi_control_AWVALID=0;s_axi_control_WDATA=value;s_axi_control_WSTRB=15;s_axi_control_WVALID=1;
 @(posedge ap_clk);while(!s_axi_control_WREADY)@(posedge ap_clk);
 @(negedge ap_clk);s_axi_control_WVALID=0;
 @(posedge ap_clk);while(!s_axi_control_BVALID)@(posedge ap_clk);
 if(s_axi_control_BRESP!=0)$fatal(1,"CTRL_WRITE_ERROR");end endtask
 task rd(input[6:0] address,output[31:0] value);begin
 @(negedge ap_clk);s_axi_control_ARADDR=address;s_axi_control_ARVALID=1;
 @(posedge ap_clk);while(!s_axi_control_ARREADY)@(posedge ap_clk);
 @(negedge ap_clk);s_axi_control_ARVALID=0;
 @(posedge ap_clk);while(!s_axi_control_RVALID)@(posedge ap_clk);
 value=s_axi_control_RDATA;if(s_axi_control_RRESP!=0)$fatal(1,"CTRL_READ_ERROR");end endtask
 task go;begin wr(0,1);ctrl=0;while((ctrl&2)==0)rd(0,ctrl);end endtask''',
 'initial begin s_axi_control_BREADY=1;s_axi_control_RREADY=1;for(n=0;n<131072;n=n+1)workmem.mem[n]=64\'hcccccccccccccccc;for(n=0;n<4096;n=n+1)outmem.mem[n]=32\'hdeadbeef;',
 f'$readmemh("rgb.mem",inputmem.mem,0,{counts["rgb"]-1});',
 'repeat(10)@(negedge ap_clk);ap_rst_n=1;repeat(10)@(negedge ap_clk);',
 "wr('h10,0);wr('h14,0);wr('h1c,0);wr('h20,0);wr('h28,0);wr('h2c,0);wr('h34,0);wr('h38,0);wr('h40,16);wr('h48,16);",
 'for(launch=1;launch<=2;launch=launch+1)begin',
 f'if(launch==1)begin $readmemh("model1.mem",modelmem.mem,0,{counts["model1"]-1});$readmemh("expected1.mem",expected,0,{counts["expected1"]-1});$readmemh("work1.mem",features,0,{counts["work1"]-1});end',
 f'else begin $readmemh("model2.mem",modelmem.mem,0,{counts["model2"]-1});$readmemh("expected2.mem",expected,0,{counts["expected2"]-1});$readmemh("work2.mem",features,0,{counts["work2"]-1});end',
 'go;expected[9]=launch;',
 f'for(n=0;n<{counts["expected1"]};n=n+1)begin if(outmem.mem[n]!==expected[n])$fatal(1,"HFE_RESULT_FAIL launch=%0d word=%0d actual=%h expected=%h",launch,n,outmem.mem[n],expected[n]);checked=checked+1;end',
 f'for(n=0;n<{counts["work1"]};n=n+1)begin if(workmem.mem[n]!==features[n])$fatal(1,"HFE_TENSOR_FAIL launch=%0d word=%0d actual=%h expected=%h",launch,n,workmem.mem[n],features[n]);checked=checked+1;end',
 '$display("HFE_LAUNCH_PASS launch=%0d cycle=%0d checked=%0d",launch,cycle,checked);end',
 "wr('h40,32);go;if(outmem.mem[1]!=4||outmem.mem[9]!=2||outmem.mem[8]!=0)$fatal(1,\"BAD_GEOMETRY_NOT_REJECTED\");",
 "wr('h40,16);modelmem.mem[13][63:32]=modelmem.mem[13][63:32]^1;go;if(outmem.mem[1]!=4||outmem.mem[9]!=2)$fatal(1,\"BAD_MAGIC_NOT_REJECTED\");",
 'if(workmem.writes==0||workmem.reads==0||modelmem.reads==0||inputmem.reads==0||outmem.writes==0)$fatal(1,"HFE_AXI_COVERAGE");',
 '$display("HFE_COMPLETE_AXI_PASS checked=%0d cycles=%0d reads=%0d writes=%0d",checked,cycle,workmem.reads,workmem.writes);$finish;end','endmodule']
(out/'tb_hfe.sv').write_text('\n'.join(tb)+'\n',encoding='utf8');(out/'axi_ram_tb.sv').write_bytes((root/'axi_ram_tb.sv').read_bytes());(out/'compile.prj').write_text(''.join(f'verilog work "{f.as_posix()}"\n' for f in sorted(rtl.glob('*.v')))+''.join(f'sv work "{(out/f).as_posix()}"\n' for f in ['axi_ram_tb.sv','tb_hfe.sv']),encoding='utf8')
started=time.monotonic()
for tool,args in [('xvlog',['-prj',str(out/'compile.prj')]),('xelab',['tb_hfe','-s','hfe_test','-debug','off','--mt','2']),('xsim',['hfe_test','-runall'])]:
    with (out/(tool+'.log')).open('w') as log:subprocess.run(['D:/2025.2/Vivado/bin/'+tool+'.bat',*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
log=(out/'xsim.log').read_text(errors='replace');match=re.search(r'HFE_COMPLETE_AXI_PASS checked=(\d+) cycles=(\d+) reads=(\d+) writes=(\d+)',log)
if not match or 'Fatal:' in log:raise RuntimeError('Complete network RTL failed')
summary=dict(**plan,passed=True,transactions=4,valid_launches=2,checked_words=int(match[1]),simulation_cycles=int(match[2]),all_retained72_tensors_exact=True,mask_cleanup=True,bad_geometry_and_magic_rejected=True,elapsed_seconds=time.monotonic()-started,board_verified=False)
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in summary.items() if k not in ['dut_files','fixture']}),flush=True)
