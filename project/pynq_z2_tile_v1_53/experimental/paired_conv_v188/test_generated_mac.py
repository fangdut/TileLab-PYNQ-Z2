"""Simulate the actual generated shared MAC with scalar-checked vectors/stalls.

This is subsystem RTL, not the whole AXI detector and not a board FPS result.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,time
from check_generated import inspect
p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parent;out=a.out.resolve();gate=inspect(a.hls)
assert gate['recurrence_safe'] and gate['capacity_gate'] and gate['shared_dot_128_dsp']
out.mkdir(parents=True,exist_ok=a.resume)
source=a.hls/'src/texture_integer.cpp';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(source)==sha(root/'texture_paired.cpp')
rtl=(a.hls/'solution/syn/verilog').resolve();top=rtl/'texture_integer_mac_row.v'
cases=[dict(ow=33,ic=576,iw=33,k=1,stride=1,pad=0,depth=0,row_head=0,nearest=0,count=1,outputs=33),dict(ow=17,ic=3,iw=33,k=3,stride=2,pad=1,depth=0,row_head=0,nearest=0,count=1,outputs=17),dict(ow=33,ic=16,iw=33,k=3,stride=1,pad=1,depth=1,row_head=2,nearest=0,count=1,outputs=33),dict(ow=1,ic=64,iw=1,k=1,stride=1,pad=0,depth=0,row_head=0,nearest=1,count=65,outputs=64),dict(ow=1,ic=64,iw=1,k=1,stride=1,pad=0,depth=0,row_head=0,nearest=1,count=1024,outputs=512),dict(ow=14,ic=24,iw=14,k=1,stride=1,pad=0,depth=0,row_head=0,nearest=0,count=1,outputs=14)]
plan=dict(source_sha256=sha(source),top_rtl_sha256=sha(top),dut_files={f.name:sha(f) for f in sorted(rtl.glob('*')) if f.suffix in ['.v','.dat']},cases=cases)
if a.resume:assert json.loads((out/'plan.json').read_text())==plan
else:
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (out/'texture_paired.cpp').write_bytes(source.read_bytes())
    for f in rtl.glob('*.dat'):(out/f.name).write_bytes(f.read_bytes())
    text=(root/'test_mac.cpp').read_text()
    emitter=r'''
static FILE *expected_file=nullptr;
template<int N> static void hexword(FILE *f,ap_uint<N> value){
    for(int j=N/32-1;j>=0;j--)std::fprintf(f,"%08x",unsigned(value.range(j*32+31,j*32)));
    std::fprintf(f,"\n");
}
static void dump_inputs(){
    char name[100];
    for(int bank=0;bank<16;bank++){
        std::sprintf(name,"case%u_ram%d.mem",cases,bank);FILE*f=std::fopen(name,"w");
        for(int n=0;n<RD;n++)hexword<64>(f,ap_uint<64>(memory[bank][n]));std::fclose(f);
    }
    std::sprintf(name,"case%u_line.mem",cases);FILE*f=std::fopen(name,"w");
    for(int n=0;n<LD;n++)hexword<128>(f,pixels[n]);std::fclose(f);
    std::sprintf(name,"case%u_dw.mem",cases);f=std::fopen(name,"w");
    for(int n=0;n<9;n++)hexword<128>(f,dw[n]);std::fclose(f);
    std::sprintf(name,"case%u_query.mem",cases);f=std::fopen(name,"w");
    for(int n=0;n<64;n++)std::fprintf(f,"%04x\n",unsigned(uint16_t(query_data[n])));std::fclose(f);
    std::sprintf(name,"case%u_expected.mem",cases);expected_file=std::fopen(name,"w");
}
'''
    text=text.replace('static void convolution(',emitter+'\nstatic void convolution(',1)
    text=text.replace('    hls::stream<sum_packet> output;','    dump_inputs();\n    hls::stream<sum_packet> output;')
    text=text.replace('sum_packet actual=output.read();','sum_packet actual=output.read();hexword<1024>(expected_file,actual);')
    text=text.replace('    require(output.empty());','    require(output.empty());std::fclose(expected_file);')
    text=text[:text.index('int main(){')]+'''int main(){
        convolution(33,576,1,1,0,false,0);
        convolution(33,3,3,2,1,false,0);
        convolution(33,16,3,1,1,true,2);
        nearest(65);nearest(1024);
        convolution(14,24,1,1,0,false,0);
        std::printf("SCALAR_CHECKED_RTL_VECTORS_PASS cases=%u checks=%u\\n",cases,checks);
    }\n'''
    (out/'emit.cpp').write_text(text)
    with (out/'compile_vectors.log').open('w') as log:subprocess.run(['D:/2025.2/Vitis/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe','-O2','-std=c++17','-static','-Wno-unknown-pragmas','-I','D:/2025.2/Vitis/include',str(out/'emit.cpp'),'-o',str(out/'emit.exe')],stdout=log,stderr=subprocess.STDOUT,check=True)
    r=subprocess.run([str(out/'emit.exe')],cwd=out,capture_output=True,text=True,check=True);(out/'vectors.log').write_text(r.stdout+r.stderr)
    assert 'SCALAR_CHECKED_RTL_VECTORS_PASS cases=6' in r.stdout
    ports=re.findall(r'^(input|output)\s*(\[\d+:0\])?\s*(\w+);',top.read_text(),re.M)
    assert len(ports)>180
    lines=['`timescale 1ns/1ps','module tb_generated_mac;']
    for direction,width,name in ports:lines.append(f'{"reg" if direction=="input" else "wire"} {width} {name}'+('=0;' if direction=='input' else ';'))
    lines+=['always #5 ap_clk=~ap_clk;','texture_integer_mac_row dut('+','.join(f'.{name}({name})' for _,_,name in ports)+');',
        'reg [63:0] memory[0:15][0:1023]; reg [127:0] pixels[0:2047],dw[0:8];reg [15:0] query_data[0:63];reg [1023:0] expected[0:511];',
        'integer cycle=0,seen=0,total=0,active_case=0,want=0,stalled=0;reg done_seen=0;',
        'always @(negedge ap_clk) begin cycle=cycle+1; sums_full_n=((cycle%7)!=0)&&((cycle%11)!=0);sums_num_data_valid=sums_full_n?0:16; end',
        'always @(posedge ap_clk) begin',
        'if(!ap_rst && sums_write && sums_full_n) begin if(seen>=want || sums_din !== expected[seen]) $fatal(1,"MAC_MISMATCH case=%0d output=%0d got=%h expected=%h",active_case,seen,sums_din,expected[seen]);seen=seen+1;total=total+1; end',
        'if(!ap_rst && !sums_full_n && active_case>0)stalled=stalled+1;']
    for bank in range(16):
        for port in [0,1]:lines.append(f'if(ram_{bank}_ce{port})ram_{bank}_q{port}<=memory[{bank}][ram_{bank}_address{port}];')
    lines+=['if(line_r_ce0)line_r_q0<=pixels[line_r_address0];','if(!ap_rst && ap_done)done_seen=1;','end','initial begin ap_rst=1;ap_continue=1;sums_fifo_cap=16;repeat(6)@(negedge ap_clk);ap_rst=0;']
    for num,case in enumerate(cases,1):
        lines.append(f'@(negedge ap_clk);active_case={num};seen=0;done_seen=0;want={case["outputs"]};')
        # Xsim readmemh does not accept a slice of a multidimensional array.
        for bank in range(16):
            lines.append(f'begin : load_{num}_{bank} reg [63:0] temp[0:1023];integer n;$readmemh("case{num}_ram{bank}.mem",temp);for(n=0;n<1024;n=n+1)memory[{bank}][n]=temp[n];end')
        for name,arr in [('line','pixels'),('dw','dw'),('query','query_data')]:lines.append(f'$readmemh("case{num}_{name}.mem",{arr});')
        lines.append(f'$readmemh("case{num}_expected.mem",expected,0,{case["outputs"]-1});')
        for key,val in case.items():
            if key!='outputs':lines.append(f'{key}={val};')
        for n in range(9):lines.append(f'dw_weight_{n}=dw[{n}];')
        for n in range(64):lines.append(f'query_{n}=query_data[{n}];')
        lines+=['@(negedge ap_clk);ap_start=1;@(negedge ap_clk);ap_start=0;','while(!done_seen)@(negedge ap_clk);',f'if(seen!=want)$fatal(1,"MAC_COUNT case={num} got=%0d expected=%0d",seen,want);',f'$display("MAC_CASE_PASS case={num} outputs=%0d cycle=%0d",seen,cycle);','repeat(6)@(negedge ap_clk);']
    lines+=['if(total!=673 || stalled==0)$fatal(1,"MAC_COVERAGE total=%0d stalled=%0d",total,stalled);','$display("GENERATED_PAIRED_MAC_RTL_PASS cases=6 outputs=%0d stalled=%0d cycles=%0d",total,stalled,cycle);$finish;end','initial begin #2000000;$fatal(1,"MAC_TIMEOUT");end','endmodule']
    # 33+17+33+64+512+14 = 673 complete 1024-bit packets.
    (out/'tb_generated_mac.sv').write_text('\n'.join(lines)+'\n')
    files=sorted(rtl.glob('*.v'));(out/'compile.prj').write_text(''.join(f'verilog work "{f.as_posix()}"\n' for f in files)+f'sv work "{(out/"tb_generated_mac.sv").as_posix()}"\n')
if a.prepare_only:print('GENERATED_MAC_RTL_PREPARED_NOT_RUN');raise SystemExit(0)
started=time.monotonic()
for tool,args in [('xvlog',['-prj',str(out/'compile.prj')]),('xelab',['tb_generated_mac','-s','mac_test','-debug','off','--mt','2']),('xsim',['mac_test','-runall'])]:
    with (out/(tool+'.log')).open('w') as log:subprocess.run(['D:/2025.2/Vivado/bin/'+tool+'.bat',*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
log=(out/'xsim.log').read_text(errors='replace');m=re.search(r'GENERATED_PAIRED_MAC_RTL_PASS cases=6 outputs=(\d+) stalled=(\d+) cycles=(\d+)',log)
if not m or 'Fatal:' in log or 'Error:' in log:raise RuntimeError('Generated MAC RTL lacks clean pass marker')
j=dict(scope='ACTUAL_DETECTOR_GENERATED_MAC_SUBSYSTEM_RTL_NOT_WHOLE_AXI_NOT_BOARD',passed=True,source_sha256=sha(source),top_rtl_sha256=sha(top),dut_files=plan['dut_files'],cases=6,packets=int(m[1]),stalled_cycles=int(m[2]),cycles=int(m[3]),elapsed_seconds=time.monotonic()-started,vector_scalar_reference_passed=True,files={f.name:sha(f) for f in out.glob('*.mem')})
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps({k:v for k,v in j.items() if k!='files'}))
