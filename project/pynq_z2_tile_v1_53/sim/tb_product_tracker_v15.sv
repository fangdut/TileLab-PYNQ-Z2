`timescale 1ns/1ps
module tb_product_tracker_v15;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,valid=0;reg [15:0] gate=0,xmin=0,xmax=0;reg [31:0] area=0,status=0;
 wire decision;wire [31:0] id,flags,score;
 product_tracker dut(clk,reset,valid,gate,xmin,xmax,area,status,decision,id,flags,score);
 task frame(input integer g,l,r,a,s,f,p);
 begin
  @(negedge clk);valid=1;gate=g;xmin=l;xmax=r;area=a;status=s;
  @(posedge clk);#1;
  if(!decision || flags!==f || id!==p) $fatal(1,"flags/id mismatch got %h/%d wanted %h/%d",flags,id,f,p);
  @(negedge clk);valid=0;
 end endtask
 initial begin
  repeat(3)@(negedge clk);reset=0;
  frame(300,10,569,500,1,27,1); // partial first alarm
  frame(300,100,659,50,1,25,1); // complete beats partial despite less area
  frame(300,360,919,40,1,25,1); // centered beats much higher count
  if(score!==32'h80000000) $fatal(1,"center distance metadata is not zero");
  frame(300,500,1059,900,1,17,1); // off center cannot replace centered
  if(score!==32'h80000118) $fatal(1,"center distance metadata must be 280");
  frame(300,360,919,41,1,25,1); // same center: more evidence wins
  frame(300,360,919,0,0,17,1); // no alarm cannot replace evidence
  frame(0,0,0,0,0,0,1); // one empty frame is not a new product
  frame(300,360,919,39,1,17,1);
  frame(0,0,0,0,0,0,1);frame(0,0,0,0,0,4,1);
  frame(300,360,919,50,1,27,2);
  @(negedge clk);reset=1;@(negedge clk);reset=0;
  frame(300,360,919,50,1,27,3); // video reset must not reuse IDs
  $display("PASS V15 product tracker: complete then centered, area tie break, partial fallback, two clear frames, reset-safe IDs");$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
