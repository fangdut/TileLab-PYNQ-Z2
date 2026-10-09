`timescale 1ns/1ps
module tb_axis_gray;
reg clk=0;always #5 clk=~clk;
reg rstn=0,mode=0,sv=0,su=0,sl=0,mr=0;reg [23:0] sd=0;
wire sr,mv,mu,ml;wire [23:0] md;
axis_gray dut(clk,rstn,mode,sd,sv,su,sl,sr,md,mv,mu,ml,mr);
reg [25:0] expected[0:12000]; integer wr=0,rd=0,n=0,cycles=0;
reg [25:0] held; reg stalled=0;
integer sum;
always @(posedge clk) begin
 if(rstn) begin
  if(stalled && {md,mu,ml} !== held) $fatal(1,"Output changed during backpressure");
  if(stalled && !mv) $fatal(1,"VALID dropped while stalled");
  if(sv&&sr) begin
   sum=77*sd[23:16]+150*sd[15:8]+29*sd[7:0];
   expected[wr]={mode?{3{8'(sum>>8)}}:sd,su,sl};wr=wr+1;
  end
  if(mv&&mr) begin
   if(rd>=wr || {md,mu,ml} !== expected[rd]) $fatal(1,"Stream mismatch at %0d",rd);
   rd=rd+1;
  end
  held={md,mu,ml};stalled=mv&&!mr;
 end else begin stalled=0;wr=0;rd=0;end
end
initial begin
 repeat(4) @(negedge clk);rstn=1;
 for(cycles=0;cycles<8000;cycles=cycles+1) begin
  @(negedge clk);
  if(!sv||sr) begin
   sv=($urandom_range(0,9)>1);sd=$urandom;mode=$urandom_range(0,1);
   su=(n%1280==0);sl=(n%1280==1279);n=n+1;
   if(cycles<8) begin sd=(cycles==0)?24'hff0000:(cycles==1)?24'h00ff00:(cycles==2)?24'h0000ff:(cycles==3)?24'hffffff:24'h000000;mode=1;sv=1;end
  end
  mr=($urandom_range(0,9)>3);
 end
 @(negedge clk);sv=0;mr=1;repeat(4) @(negedge clk);
 if(wr!=rd || rd<1000) $fatal(1,"Missing output");
 // Reset discards an occupied/stalled entry.
 sv=1;mr=0; @(negedge clk);rstn=0; @(negedge clk);
 if(mv) $fatal(1,"Reset did not clear valid");
 $display("PASS AXIS: randomized data, modes, stalls, sidebands, reset; transfers=%0d",n);$finish;
end
endmodule
