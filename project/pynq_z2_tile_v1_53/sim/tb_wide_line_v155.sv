`timescale 1ns/1ps
module tb_wide_line_v155;
 localparam W=80,H=64,HT=112,VT=100,TOP=4,F=4,LAG=16*HT+18;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,de=0,hs=0,vs=0;reg [7:0] gray=0;reg [23:0] rgb=0;
 wire [23:0] rgb_out;wire od,oh,ov;wire [7:0] narrow,wide,mean_short,mean_long,mean_line;wire [3:0] direction_weak;
 wide_line_dual_valley_v155 #(.WIDTH(W),.HEIGHT(H),.H_TOTAL(HT)) dut(
  clk,reset,gray,rgb,de,hs,vs,rgb_out,od,oh,ov,narrow,wide,mean_short,mean_long,mean_line,direction_weak);
 reg [3:0] expected_dir[0:F*W*H-1];
 reg [7:0] pixels[0:F*W*H-1],expected8[0:F*W*H-1],expected16[0:F*W*H-1],expected_short[0:F*W*H-1],expected_long[0:F*W*H-1],expected_line[0:F*W*H-1];
 reg [26:0] q[0:LAG-1];integer ptr=0,checks=0,idx=0;
 string root,result;integer proof;
 task tick(input bit d,h,v,input [23:0] tag,input [7:0] g);
  @(negedge clk);de=d;hs=h;vs=v;rgb=tag;gray=g;
  @(posedge clk);#1;
  if({ov,oh,od,rgb_out}!==q[ptr])$fatal(1,"RGB/sync alignment got=%h expected=%h",{ov,oh,od,rgb_out},q[ptr]);
  if(od)begin
   idx=rgb_out[15:0];
   if(rgb_out[23:16]!=8'ha5 || idx>=F*W*H)$fatal(1,"Corrupt tag %h",rgb_out);
   if(mean_short!==expected_short[idx] || mean_long!==expected_long[idx])
    $fatal(1,"Mean idx=%0d f=%0d x=%0d y=%0d got=%0d/%0d expected=%0d/%0d",idx,idx/(W*H),idx%W,(idx/W)%H,mean_short,mean_long,expected_short[idx],expected_long[idx]);
   if(narrow!==expected8[idx] || wide!==expected16[idx])$fatal(1,"Valley idx=%0d got=%d/%d expected=%d/%d",idx,narrow,wide,expected8[idx],expected16[idx]);
   if(mean_line!==expected_line[idx])$fatal(1,"Wide line idx=%0d got=%0d expected=%0d",idx,mean_line,expected_line[idx]);
   if(direction_weak!==expected_dir[idx])$fatal(1,"Direction idx=%0d got=%h expected=%h",idx,direction_weak,expected_dir[idx]);
   checks++;
  end
  q[ptr]={v,h,d,tag};ptr=(ptr+1)%LAG;
 endtask
 initial begin
  if(!$value$plusargs("ROOT=%s",root))$fatal(1,"ROOT required");
  if(!$value$plusargs("RESULT=%s",result))$fatal(1,"RESULT required");
  $readmemh({root,"/gray.mem"},pixels);$readmemh({root,"/score8.mem"},expected8);$readmemh({root,"/score16.mem"},expected16);$readmemh({root,"/short.mem"},expected_short);$readmemh({root,"/long.mem"},expected_long);$readmemh({root,"/line.mem"},expected_line);
  $readmemh({root,"/dir.mem"},expected_dir);
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
  proof=$fopen(result,"w");if(!proof)$fatal(1,"Cannot write success proof");
  $fdisplay(proof,"PASS %0d exact pixels, five scores, four directions, RGB and sync",checks);$fclose(proof);
  $display("PASS WIDE LINE: %0d exact pixels, 5 scores, border behavior, changing frames, RGB and all syncs",checks);$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
