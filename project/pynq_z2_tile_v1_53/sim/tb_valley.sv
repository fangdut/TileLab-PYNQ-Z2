`timescale 1ns/1ps
module tb_valley;
 localparam W=48,H=36,HT=64,VT=60;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,de=0,hs=0,vs=0;reg[7:0] gray=0;reg[23:0] rgb=0;
 wire[23:0] out;wire od,oh,ov;wire[7:0] score;
 directional_valley #(.WIDTH(W),.HEIGHT(H),.H_TOTAL(HT)) dut(clk,reset,gray,rgb,de,hs,vs,out,od,oh,ov,score);
 reg[7:0] pixels[0:W*H-1],expected[0:W*H-1];integer x,y,f,idx,checks=0,errors=0;
 string root;
 always @(posedge clk)begin
  #1;
  if(!reset && od)begin
   idx=out[15:0];
   if(out[23:16]!=8'hA5 || idx>=W*H)$fatal(1,"Original alignment corrupt %x",out);
   if(score!==expected[idx])begin
    if(errors<12)$display("Mismatch idx=%0d x=%0d y=%0d got=%0d expected=%0d",idx,idx%W,idx/W,score,expected[idx]);
    errors=errors+1;
   end
   checks=checks+1;
  end
 end
 initial begin
  if(!$value$plusargs("ROOT=%s",root))$fatal(1,"ROOT missing");
  $readmemh({root,"/sim/valley_gray.mem"},pixels);$readmemh({root,"/sim/valley_score.mem"},expected);
  repeat(20)@(negedge clk);reset=0;
  for(f=0;f<3;f=f+1)for(y=0;y<VT;y=y+1)for(x=0;x<HT;x=x+1)begin
   @(negedge clk);vs=(y<2);hs=(x>=52 && x<56);de=(y>=4 && y<4+H && x<W);
   if(de)begin gray=pixels[(y-4)*W+x];rgb=24'hA50000|((y-4)*W+x);end else begin gray=0;rgb=0;end
  end
  @(negedge clk);de=0;vs=0;repeat(HT*12)@(negedge clk);
  if(errors || checks!=W*H*3)$fatal(1,"VALLEY FAIL errors=%0d pixels=%0d",errors,checks);
  $display("VALLEY PASS pixels=%0d",checks);$finish;
 end
endmodule
