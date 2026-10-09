`timescale 1ns/1ps
module tb_quad_hysteresis;
 localparam W=48,H=36,HT=64,VT=46,N=12;
 reg clk=0;always #5 clk=~clk;
 reg extra=0;reg reset=1,de=0,hs=0,vs=0,si=0,wi=0;reg [31:0] tag=0;
 wire m1,w1,d1,h1,v1,m2,w2,d2,h2,v2;wire [31:0] t1,t2;
 raster_morph #(.WIDTH(W),.HEIGHT(H),.H_TOTAL(HT),.SIDE_WIDTH(32)) a(
 clk,reset,1'b0,si,de,hs,vs,tag,m1,d1,h1,v1,t1,1'b1,wi,w1);
 raster_morph #(.WIDTH(W),.HEIGHT(H),.H_TOTAL(HT),.SIDE_WIDTH(32)) b(
 clk,reset,1'b0,m1,d1,h1,v1,t1,m2,d2,h2,v2,t2,1'b1,w1,w2);
 wire m3,w3,d3,h3,v3,m4,w4,d4,h4,v4;wire [31:0] t3,t4;
 raster_morph #(.WIDTH(W),.HEIGHT(H),.H_TOTAL(HT),.SIDE_WIDTH(32),.BYPASS_WHEN_NOT_GROW(1)) c(
 clk,reset,1'b0,m2,d2,h2,v2,t2,m3,d3,h3,v3,t3,extra,w2,w3);
 raster_morph #(.WIDTH(W),.HEIGHT(H),.H_TOTAL(HT),.SIDE_WIDTH(32),.BYPASS_WHEN_NOT_GROW(1)) d(
 clk,reset,1'b0,m3,d3,h3,v3,t3,m4,d4,h4,v4,t4,extra,w3,w4);
 reg [1:0] samples[0:W*H*N-1];reg expected[0:W*H*N-1];
 integer x,y,f,idx,checks=0,errors=0;string root;
 always @(posedge clk)begin
  #1;
  if(!reset && d4)begin
   idx=t4[23:0];
   if(t4[31:24]!=8'hA6 || idx>=W*H*N)$fatal(1,"Sideband alignment %x",t4);
   if(m4!==expected[idx])begin
    if(errors<12)$display("Mismatch idx=%0d xy=%0d,%0d got=%b want=%b",idx,idx%W,(idx/W)%H,m4,expected[idx]);
    errors=errors+1;
   end
   checks=checks+1;
  end
 end
 initial begin
  if(!$value$plusargs("ROOT=%s",root))$fatal(1,"ROOT missing");
  $readmemh({root,"/sim/quad_input.mem"},samples);$readmemh({root,"/sim/quad_expected.mem"},expected);
  repeat(20)@(negedge clk);reset=0;
  for(f=0;f<N;f=f+1)for(y=0;y<VT;y=y+1)for(x=0;x<HT;x=x+1)begin
   @(negedge clk);extra=(f<6);vs=(y<2);hs=(x>=52 && x<56);de=(y>=4 && y<4+H && x<W);
   if(de)begin idx=f*W*H+(y-4)*W+x;{wi,si}=samples[idx];tag=32'hA6000000|idx;end
   else begin si=0;wi=0;tag=0;end
  end
  @(negedge clk);de=0;vs=0;repeat(HT*6)@(negedge clk);
  if(errors || checks!=W*H*N)$fatal(1,"QUAD FAIL errors=%0d checks=%0d",errors,checks);
  $display("QUAD HYSTERESIS PASS pixels=%0d",checks);$finish;
 end
endmodule
