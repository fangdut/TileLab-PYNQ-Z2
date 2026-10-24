"""Complete generated detector RTL, lightweight AXI memories, two launches.

Uses independent pre-existing fixture outputs/features, not a synthetic FPS.
No UVM agents; every DUT RTL/ROM/fixture byte is bound into the proof.
"""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,time
from check_generated import inspect
p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--vectors',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parent;out=a.out.resolve();rtl=(a.hls/'solution/syn/verilog').resolve();sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();gate=inspect(a.hls)
assert gate['recurrence_safe'] and gate['capacity_gate'] and gate['shared_dot_128_dsp']
assert sha(a.hls/'src/texture_integer.cpp')==sha(root/'texture_spatial_pair.cpp')
names=['test_model.bin','test_rgb.bin','test_expected.bin','test_fa_expected.bin','test_fb_expected.bin'];fixture={n:sha(a.vectors/n) for n in names}
plan=dict(source_sha256=gate['source_sha256'],dut_files={f.name:sha(f) for f in sorted(rtl.glob('*')) if f.suffix in ['.v','.dat']},fixture=fixture,test_driver_sha256=sha(Path(__file__)),axi_memory_sha256=sha(root/'axi_ram_tb.sv'),input_width=79,input_height=65)
out.mkdir(parents=True,exist_ok=a.resume)
if a.resume:assert json.loads((out/'plan.json').read_text())==plan
else:
 (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
 for f in rtl.glob('*.dat'):(out/f.name).write_bytes(f.read_bytes())
 for n in names:(out/n).write_bytes((a.vectors/n).read_bytes())
 def hexfile(name,wordbytes):
  data=(out/(name+'.bin')).read_bytes();assert len(data)%wordbytes==0
  (out/(name+'.mem')).write_text(''.join(f'{int.from_bytes(data[i:i+wordbytes],"little"):0{wordbytes*2}x}\n' for i in range(0,len(data),wordbytes)))
  return len(data)//wordbytes
 counts={n[:-4]:hexfile(n[:-4],8 if n=='test_model.bin' else 4) for n in names}
 header=struct.unpack_from('<64I',(out/'test_model.bin').read_bytes());assert header[16]<=32768*16 and counts['test_expected']<8192 and counts['test_rgb']==79*65
 text=(rtl/'texture_integer.v').read_text();params=re.findall(r'^parameter\s+(C_\w+)\s*=\s*([^;]+);',text,re.M)
 ports=re.findall(r'^(input|output)\s*(\[[^\n]+?\])?\s*(\w+);',text,re.M);assert len(ports)>150
 tb=['`timescale 1ns/1ps','module tb_full_axi;']+[f'localparam {name}={val};' for name,val in params]
 for direction,width,name in ports:
  kind='reg' if direction=='input' and not name.startswith('m_axi_') else 'wire'
  tb.append(f'{kind} {width} {name}'+('=0;' if kind=='reg' else ';'))
 tb+=['always #5 ap_clk=~ap_clk;','texture_integer dut('+','.join(f'.{name}({name})' for _,_,name in ports)+');']
 for bus,words in [('modelmem',65536),('workmem',32768),('inputmem',8192),('outmem',8192)]:
  signals='AWVALID AWREADY AWADDR AWID AWLEN AWSIZE AWBURST WVALID WREADY WDATA WSTRB WLAST BVALID BREADY BID BRESP ARVALID ARREADY ARADDR ARID ARLEN ARSIZE ARBURST RVALID RREADY RDATA RLAST RID RRESP'.split()
  tb.append(f'axi_ram_tb #(.D(C_M_AXI_{bus.upper()}_DATA_WIDTH),.WORDS({words})) {bus}(.clk(ap_clk),.rst_n(ap_rst_n),'+','.join(f'.{s}(m_axi_{bus}_{s})' for s in signals)+');')
  tb +=[f'assign m_axi_{bus}_BUSER=0;',f'assign m_axi_{bus}_RUSER=0;']
 tb+=['integer cycle=0,n,launch,checked=0;reg[31:0] status_word,reference_word;reg[31:0] expected[0:8191],fa[0:8191],fb[0:8191];',
 'always @(posedge ap_clk)cycle<=cycle+1;',
 '''task ctrl_write(input[6:0] address,input[31:0] value);begin
 @(negedge ap_clk);s_axi_control_AWADDR=address;s_axi_control_AWVALID=1;
 @(posedge ap_clk);while(!s_axi_control_AWREADY)@(posedge ap_clk);
 @(negedge ap_clk);s_axi_control_AWVALID=0;s_axi_control_WDATA=value;s_axi_control_WSTRB=15;s_axi_control_WVALID=1;
 @(posedge ap_clk);while(!s_axi_control_WREADY)@(posedge ap_clk);
 @(negedge ap_clk);s_axi_control_WVALID=0;
 @(posedge ap_clk);while(!s_axi_control_BVALID)@(posedge ap_clk);
 if(s_axi_control_BRESP!=0)$fatal(1,"AXIL_WRITE_RESPONSE");
 end endtask
 task ctrl_read(input[6:0] address,output[31:0] value);begin
 @(negedge ap_clk);s_axi_control_ARADDR=address;s_axi_control_ARVALID=1;
 @(posedge ap_clk);while(!s_axi_control_ARREADY)@(posedge ap_clk);
 @(negedge ap_clk);s_axi_control_ARVALID=0;
 @(posedge ap_clk);while(!s_axi_control_RVALID)@(posedge ap_clk);
 value=s_axi_control_RDATA;if(s_axi_control_RRESP!=0)$fatal(1,"AXIL_READ_RESPONSE");
 end endtask''',
 'initial begin s_axi_control_BREADY=1;s_axi_control_RREADY=1;',
 'for(n=0;n<32768;n=n+1)workmem.mem[n]=0;for(n=0;n<8192;n=n+1)outmem.mem[n]=32\'hdeadbeef;',
 f'$readmemh("test_model.mem",modelmem.mem,0,{counts["test_model"]-1});',f'$readmemh("test_rgb.mem",inputmem.mem,0,{counts["test_rgb"]-1});',
 f'$readmemh("test_expected.mem",expected,0,{counts["test_expected"]-1});',f'$readmemh("test_fa_expected.mem",fa,0,{counts["test_fa_expected"]-1});',f'$readmemh("test_fb_expected.mem",fb,0,{counts["test_fb_expected"]-1});',
 'repeat(10)@(negedge ap_clk);ap_rst_n=1;repeat(10)@(negedge ap_clk);',
 'ctrl_write(7\'h10,0);ctrl_write(7\'h14,0);ctrl_write(7\'h1c,0);ctrl_write(7\'h20,0);ctrl_write(7\'h28,0);ctrl_write(7\'h2c,0);ctrl_write(7\'h34,0);ctrl_write(7\'h38,0);ctrl_write(7\'h40,79);ctrl_write(7\'h48,65);',
 'for(launch=1;launch<=2;launch=launch+1)begin',
 'if(launch==2)modelmem.mem[7][63:32]=32\'h40000000;',
 'ctrl_write(0,1);status_word=0;while((status_word&2)==0)ctrl_read(0,status_word);',
 f'for(n=0;n<{counts["test_expected"]};n=n+1)begin reference_word=expected[n];',
 f'if(launch==2)begin if(n==2||n==6||n>={16+header[4]*header[4]})reference_word=0;if(n==4)reference_word=32\'h40000000;if(n==9)reference_word=2;end',
 'if(outmem.mem[n]!==reference_word)$fatal(1,"FULL_AXI_RESULT_FAIL launch=%0d word=%0d got=%h expected=%h",launch,n,outmem.mem[n],reference_word);checked=checked+1;end',
 f'for(n=0;n<{counts["test_fa_expected"]};n=n+1)begin if(workmem.mem[{header[7]}+n/4][(n%4)*32+:32]!==fa[n])$fatal(1,"FULL_AXI_FEATURE_A_FAIL launch=%0d word=%0d",launch,n);checked=checked+1;end',
 f'for(n=0;n<{counts["test_fb_expected"]};n=n+1)begin if(workmem.mem[{header[8]}+n/4][(n%4)*32+:32]!==fb[n])$fatal(1,"FULL_AXI_FEATURE_B_FAIL launch=%0d word=%0d",launch,n);checked=checked+1;end',
 '$display("FULL_AXI_LAUNCH_PASS launch=%0d cycle=%0d checked=%0d",launch,cycle,checked);end',
 'if(workmem.writes==0||workmem.reads==0||outmem.writes==0||modelmem.reads==0||inputmem.reads==0)$fatal(1,"FULL_AXI_COVERAGE");',
 '$display("PAIRED_FULL_AXI_RTL_PASS launches=2 checked=%0d cycles=%0d work_reads=%0d work_writes=%0d",checked,cycle,workmem.reads,workmem.writes);$finish;end',
 'initial begin #100000000;$fatal(1,"FULL_AXI_TIMEOUT");end','endmodule']
 (out/'tb_full_axi.sv').write_text('\n'.join(tb)+'\n');(out/'axi_ram_tb.sv').write_bytes((root/'axi_ram_tb.sv').read_bytes())
 (out/'compile.prj').write_text(''.join(f'verilog work "{f.as_posix()}"\n' for f in sorted(rtl.glob('*.v')))+''.join(f'sv work "{(out/f).as_posix()}"\n' for f in ['axi_ram_tb.sv','tb_full_axi.sv']))
if a.prepare_only:print('FULL_AXI_RTL_PREPARED_NOT_RUN');raise SystemExit(0)
started=time.monotonic()
for tool,args in [('xvlog',['-prj',str(out/'compile.prj')]),('xelab',['tb_full_axi','-s','full_test','-debug','off','--mt','2']),('xsim',['full_test','-runall'])]:
 with (out/(tool+'.log')).open('w') as log:subprocess.run(['D:/2025.2/Vivado/bin/'+tool+'.bat',*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800)
log=(out/'xsim.log').read_text(errors='replace');m=re.search(r'PAIRED_FULL_AXI_RTL_PASS launches=2 checked=(\d+) cycles=(\d+) work_reads=(\d+) work_writes=(\d+)',log)
if not m or 'Fatal:' in log or 'Error:' in log:raise RuntimeError('Complete AXI RTL did not pass')
proof=dict(scope='COMPLETE_GENERATED_DETECTOR_AXI_RTL_TWO_LAUNCHES_NOT_BOARD',passed=True,**plan,launches=2,checked_words=int(m[1]),simulation_cycles=int(m[2]),work_reads=int(m[3]),work_writes=int(m[4]),elapsed_seconds=time.monotonic()-started,results_exact=True,intermediate_features_exact=True,second_launch_alarm_and_mask_cleanup=True,fixture_scope='Frozen reduced graph with576-input convolution,24-output tails,3x3/depthwise/residual/projection/nearest/mask; not117 real-photo RTL runs',testbench_sha256=sha(out/'tb_full_axi.sv'),xsim_log_sha256=sha(out/'xsim.log'))
(out/'summary.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k not in ['dut_files','fixture']}))
