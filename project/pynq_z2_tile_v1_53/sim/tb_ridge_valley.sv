`timescale 1ns/1ps
module tb_ridge_valley;
 localparam W=80,H=64,HT=112,VT=100,TOP=4,F=4,LAG=16*HT+18;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,de=0,hs=0,vs=0;reg [7:0] gray=0;reg [23:0] rgb=0;
 wire [23:0] rgb_out;wire od,oh,ov;wire [7:0] narrow,wide,ridge;
 ridge_dual_scale_valley #(.WIDTH(W),.HEIGHT(H),.H_TOTAL(HT)) dut(
  clk,reset,gray,rgb,de,hs,vs,rgb_out,od,oh,ov,narrow,wide,ridge);
 reg [7:0] pixels[0:F*W*H-1],expected8[0:F*W*H-1],expected16[0:F*W*H-1],expected_ridge[0:F*W*H-1];
 reg [26:0] q[0:LAG-1];integer ptr=0,checks=0,idx=0;
 string root;
 task tick(input bit d,h,v,input [23:0] tag,input [7:0] g);
  @(negedge clk);de=d;hs=h;vs=v;rgb=tag;gray=g;
  @(posedge clk);#1;
  if({ov,oh,od,rgb_out}!==q[ptr])$fatal(1,"RGB/sync alignment got=%h expected=%h",{ov,oh,od,rgb_out},q[ptr]);
  if(od)begin
   idx=rgb_out[15:0];
   if(rgb_out[23:16]!=8'ha5 || idx>=F*W*H)$fatal(1,"Corrupt tag %h",rgb_out);
   if(ridge!==expected_ridge[idx])$fatal(1,"Ridge idx=%0d f=%0d x=%0d y=%0d got=%0d expected=%0d",idx,idx/(W*H),idx%W,(idx/W)%H,ridge,expected_ridge[idx]);
   if(narrow!==expected8[idx] || wide!==expected16[idx])$fatal(1,"Valley idx=%0d got=%d/%d expected=%d/%d",idx,narrow,wide,expected8[idx],expected16[idx]);
   checks++;
  end
  q[ptr]={v,h,d,tag};ptr=(ptr+1)%LAG;
 endtask
 initial begin
  if(!$value$plusargs("ROOT=%s",root))$fatal(1,"ROOT required");
  $readmemh({root,"/gray.mem"},pixels);$readmemh({root,"/score8.mem"},expected8);$readmemh({root,"/score16.mem"},expected16);$readmemh({root,"/ridge.mem"},expected_ridge);
  for(integer i=0;i<LAG;i++)q[i]=0;
  repeat(30)@(negedge clk);reset=0;
  for(integer f=0;f<F;f++)begin
   for(integer y=0;y<VT;y++)for(integer x=0;x<HT;x++)begin
    integer index;bit active;
    active=(y>=TOP && y<TOP+H && x<W);index=f*W*H+(y-TOP)*W+x;
    tick(active,x>=W+4 && x<W+12,y<2,active?(24'ha50000|index):0,active?pixels[index]:0);
   end
  end
  for(integer i=0;i<LAG+20;i++)tick(0,0,0,0,0);
  if(checks!=F*W*H)$fatal(1,"Bad pixel count %0d",checks);
  $display("PASS COHERENT RIDGE: %0d exact pixels, 3 scores, border behavior, changing frames, RGB and all syncs",checks);$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
