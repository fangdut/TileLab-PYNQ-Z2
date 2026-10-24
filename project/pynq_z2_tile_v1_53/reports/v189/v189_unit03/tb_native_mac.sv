`timescale 1ns/1ps
module tb_native_mac;
reg clk=0,rst=1,ce=0,nearest=0,valid_in=0;reg[63:0] act=0;reg[1023:0] c0=0,c1=0,q=0;wire[959:0] result;
always #5 clk=~clk;
shared_mac dut(.ap_clk(clk),.ap_rst(rst),.ap_ce(ce),.nearest(nearest),.activations(act),.centers0(c0),.centers1(c1),.query_bits(q),.ap_return(result));
reg modes[0:2047];reg[63:0] acts[0:2047];reg[1023:0] centers0[0:2047],centers1[0:2047],queries[0:2047];reg[959:0] expecteds[0:2047],pipe[0:5],reference_in;
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
 while(index<2048)begin
  @(negedge clk);cycle=cycle+1;rst=(cycle%251==0);ce=(cycle%7!=0)&&(cycle%11!=0);valid_in=!rst&&ce;
  if(valid_in)begin nearest=modes[index];act=acts[index];c0=centers0[index];c1=centers1[index];q=queries[index];reference_in=expecteds[index];index=index+1;end
 end
 @(negedge clk);valid_in=0;rst=0;ce=1;repeat(10)@(negedge clk);
 if(issued!=2048||checked+flushed!=issued||stalled==0||flushed==0)$fatal(1,"NATIVE_SHARED_MAC_RTL_COVERAGE issued=%0d checked=%0d flushed=%0d",issued,checked,flushed);
 $display("NATIVE_SHARED_MAC_RTL_PASS checked=%0d issued=%0d flushed=%0d stalled=%0d reset_cycles=%0d",checked,issued,flushed,stalled,reset_count);$finish;
end
initial begin #1000000;$fatal(1,"NATIVE_SHARED_MAC_RTL_TIMEOUT");end
endmodule
