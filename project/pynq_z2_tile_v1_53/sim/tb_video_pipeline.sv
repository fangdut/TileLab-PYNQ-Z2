`timescale 1ns/1ps
module tb_video_pipeline;
 parameter W=1280,H=720,HT=1650,VT=750,TOP=25;
 localparam LAG=HT+7;
 reg clk=0,cclk=0;always #5 clk=~clk;always #3.5 cclk=~cclk;
 reg reset=1,de=0,hs=0,vs=0;reg [1:0] mode=0;reg [23:0] rgb=0;
 wire [23:0] out;wire ode,ohs,ovs,ok,pr,wv;wire [1:0] active;
 wire [31:0] frames,pixels;wire [15:0] lines,width;
 video_core #(.WIDTH(W),.HEIGHT(H),.H_TOTAL(HT)) dut(
 .pixel_clk(clk),.control_clk(cclk),.reset(reset),.mode_request(mode),
 .rgb_in(rgb),.de_in(de),.hs_in(hs),.vs_in(vs),.rgb_out(out),.de_out(ode),.hs_out(ohs),.vs_out(ovs),
 .frame_count(frames),.frame_pixels(pixels),.frame_lines(lines),.line_pixels(width),.format_ok(ok),
 .mode_active(active),.pixel_reset(pr),.window_valid(wv));
 reg [26:0] expected[0:LAG-1];integer ptr=0,checked=0,oframes=0,image_epoch=0;reg lastvs=0;integer dumpfd=0,gaussfd=0;
 function automatic [23:0] color(input integer x,y);
  integer r,g,b;begin
   r=(x*3+y*7+(x/16)*51+image_epoch*41)%256;g=(x*11+y*5+(y/9)*79+image_epoch*93)%256;b=(x*7+y*13+image_epoch*157)%256;
   color={8'(r),8'(b),8'(g)};
  end
 endfunction
 function automatic integer gray(input integer x,y);
  reg [23:0] c;begin c=color(x,y);gray=(77*c[23:16]+150*c[7:0]+29*c[15:8])>>8;end
 endfunction
 function automatic [23:0] golden(input integer x,y,m);
  integer gx,gy,s;begin
   if(m==0) golden=color(x,y);
   else if(m==1) golden={3{8'(gray(x,y))}};
   else if(x==0 || y==0 || x==W-1 || y==H-1) golden=0;
   else if(m==3) begin
    s=(gray(x-1,y-1)+2*gray(x,y-1)+gray(x+1,y-1)
       +2*gray(x-1,y)+4*gray(x,y)+2*gray(x+1,y)
       +gray(x-1,y+1)+2*gray(x,y+1)+gray(x+1,y+1))>>4;
    golden={3{8'(s)}};
   end else begin
    gx=gray(x+1,y-1)+2*gray(x+1,y)+gray(x+1,y+1)-gray(x-1,y-1)-2*gray(x-1,y)-gray(x-1,y+1);
    gy=gray(x-1,y+1)+2*gray(x,y+1)+gray(x+1,y+1)-gray(x-1,y-1)-2*gray(x,y-1)-gray(x+1,y-1);
    s=((gx<0)?-gx:gx)+((gy<0)?-gy:gy);if(s>255)s=255;golden={3{8'(s)}};
   end
  end
 endfunction
 task tick(input bit d,h,v,input [23:0] c,gold);
  @(negedge clk);de=d;hs=h;vs=v;rgb=c;
  @(posedge clk);#1;
  if({ovs,ohs,ode}!==expected[ptr][26:24]) $fatal(1,"sync mismatch time=%t ptr=%0d got=%b expected=%b",$time,ptr,{ovs,ohs,ode},expected[ptr][26:24]);
  if(ode) begin
   if(out!==expected[ptr][23:0]) $fatal(1,"pixel mismatch n=%0d got=%h expected=%h mode=%0d",checked,out,expected[ptr][23:0],active);
   if(dumpfd && checked>=2*W*H && checked<3*W*H)
    $fwrite(dumpfd,"%c%c%c",out[23:16],out[7:0],out[15:8]);
   if(gaussfd && checked>=3*W*H && checked<4*W*H)
    $fwrite(gaussfd,"%c%c%c",out[23:16],out[7:0],out[15:8]);
   checked++;
  end
  if(ovs && !lastvs) oframes++;lastvs=ovs;
  expected[ptr]={v,h,d,gold};ptr=(ptr==LAG-1)?0:ptr+1;
 endtask
 initial begin
  if(W==1280 && H==720) begin
   dumpfd=$fopen("sobel_sim_epoch0.rgb","wb");if(!dumpfd)$fatal(1,"cannot open simulation pixel dump");
   gaussfd=$fopen("gaussian_sim_epoch0.rgb","wb");if(!gaussfd)$fatal(1,"cannot open Gaussian dump");
  end
  for(integer j=0;j<LAG;j++) expected[j]=0;
  repeat(5) @(negedge clk);reset=0;repeat(10) @(negedge clk);
  for(integer f=0;f<4;f++) begin
   for(integer ry=0;ry<VT;ry++) for(integer x=0;x<HT;x++) begin
    if(ry==TOP+H/2 && x==5 && f<3) mode=f+1;
    tick(ry>=TOP && ry<TOP+H && x<W,x>=W+110 && x<W+150,ry<5,
     color(x,ry-TOP),golden(x,ry-TOP,f));
    if(ry>=TOP && active!=f) $fatal(1,"mode changed inside frame");
   end
  end
  // Next VS closes third frame, then flush the fixed line delay.
  for(integer j=0;j<HT+30;j++) tick(0,0,j<5,0,0);
  if(checked!=4*W*H || oframes!=5) $fatal(1,"pixel or frame count mismatch %0d %0d",checked,oframes);
  if(W==1280 && H==720 && (!ok || frames!=4 || pixels!=921600 || lines!=720 || width!=1280)) $fatal(1,"720p statistics mismatch");
  // Lock-loss resets mask stale BRAM before a fresh frame sequence.
  reset=1;repeat(8) @(negedge clk);
  if(ode || ok || frames || active) $fatal(1,"reset did not clear output/status");
  for(integer j=0;j<LAG;j++)expected[j]=0;
  ptr=0;lastvs=0;image_epoch=1;reset=0;repeat(10) @(negedge clk);
  // Changed pixels after lock loss catch stale line/raster RAM content.
  for(integer ry=0;ry<VT;ry++)for(integer xx=0;xx<HT;xx++)
   tick(ry>=TOP && ry<TOP+H && xx<W,xx>=W+110 && xx<W+150,ry<5,
     color(xx,ry-TOP),golden(xx,ry-TOP,3));
  for(integer j=0;j<HT+30;j++)tick(0,0,j<5,0,0);
  if(checked!=5*W*H || active!=3) $fatal(1,"post-reset Gaussian recovery failed");
  if(W==1280 && (!ok || frames!=1))$fatal(1,"post-reset statistics failed");
  if(dumpfd)$fclose(dumpfd);if(gaussfd)$fclose(gaussfd);
  $display("PASS PIPELINE V04: %0d pixels, four modes, centered Sobel and Gaussian, all borders, sync lag=%0d, frame switching and changed-image recovery after reset",checked,LAG);$finish;
 end
 initial begin #100000000;$fatal(1,"Timeout");end
endmodule
