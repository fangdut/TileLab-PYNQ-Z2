`timescale 1ns/1ps
// Independent weighted-sum reference, checked on each HLS handshake completion.
module tb_quarter;
 reg clk=0;always #4 clk=~clk;reg reset=1;
 reg hs=0,vs=0;reg [7:0] a=0,b=0;reg [1:0] hf=0,vf=0;
 reg [11:0] top=0,bottom=0;wire [11:0] ho;wire [15:0] vo;
 wire hd,hi,hr,vd,vi,vr;
 texture_integer_quarter_horizontal h(.ap_clk(clk),.ap_rst(reset),.ap_ce(1'b1),
  .ap_start(hs),.ap_done(hd),.ap_idle(hi),.ap_ready(hr),.a(a),.b(b),.f(hf),.ap_return(ho));
 texture_integer_quarter_vertical v(.ap_clk(clk),.ap_rst(reset),
  .ap_start(vs),.ap_done(vd),.ap_idle(vi),.ap_ready(vr),.top(top),.bottom(bottom),.f(vf),.ap_return(vo));
 integer hc=0,vc=0;
 task horizontal(input integer aa,bb,ff);
 integer expect_value,waited;begin
  expect_value=(4-ff)*aa+ff*bb;
  @(negedge clk);a=aa;b=bb;hf=ff;hs=1;
  @(negedge clk);hs=0;waited=0;
  while(!hd)begin @(negedge clk);waited++;if(waited>8)$fatal(1,"Horizontal watchdog");end
  if($signed(ho)!==expect_value)$fatal(1,"Horizontal mismatch %d/%d",$signed(ho),expect_value);
  hc++;
 end endtask
 task vertical(input integer aa,bb,ff);
 integer expect_value,waited;begin
  expect_value=(4-ff)*aa+ff*bb;
  @(negedge clk);top=aa;bottom=bb;vf=ff;vs=1;
  @(negedge clk);vs=0;waited=0;
  while(!vd)begin @(negedge clk);waited++;if(waited>8)$fatal(1,"Vertical watchdog");end
  if($signed(vo)!==expect_value)$fatal(1,"Vertical mismatch %d/%d",$signed(vo),expect_value);
  vc++;
 end endtask
 reg [31:0] rng=32'h185ab211;
 function [31:0] random32();begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);random32=rng;end endfunction
 integer i,j,k;
 initial begin
  repeat(4)@(negedge clk);reset=0;repeat(2)@(negedge clk);
  fork
   begin
    for(integer n=0;n<262144;n++)horizontal(((n>>10)&255)-128,((n>>2)&255)-128,n&3);
   end
   begin
    for(integer f=0;f<4;f++)begin vertical(-512,-512,f);vertical(-512,508,f);vertical(508,-512,f);vertical(508,508,f);end
    for(integer n=0;n<131072;n++)vertical(int'(random32()%1021)-512,int'(random32()%1021)-512,random32()%4);
   end
  join
  if(hc!=262144||vc!=131088)$fatal(1,"Coverage missing");
  $display("QUARTER_PIPELINE_GENERATED_RTL_EXACT_PASS horizontal=%0d vertical=%0d",hc,vc);$finish;
 end
 initial begin #30000000;$fatal(1,"Global watchdog");end
endmodule
