`timescale 1ns/1ps
module tb_window3x3;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,ce=0,iv=0;reg [7:0] pix=0;reg [15:0] x=0,y=0;
 wire ov,border;wire [71:0] win;wire [15:0] ox,oy;
 window3x3 #(.WIDTH(8)) dut(clk,reset,ce,iv,pix,x,y,ov,ox,oy,win,border);
 integer checks=0,epoch=0;reg [105:0] held;
 function automatic [7:0] pixel(input integer xx,yy);pixel=(xx*17+yy*39+epoch*73)%256;endfunction
 task step(input bit en,valid,input integer xx,yy);
  @(negedge clk);held={ov,border,ox,oy,win};ce=en;iv=valid;x=xx;y=yy;pix=pixel(xx,yy);
  @(posedge clk);#1;
  if(!en && {ov,border,ox,oy,win}!==held) $fatal(1,"CE pause changed window");
  if(en && ov) begin
   if(border !== (ox<2 || oy<2)) $fatal(1,"border flag incorrect");
   if(!border) begin
    if(win!=={pixel(ox-2,oy-2),pixel(ox-1,oy-2),pixel(ox,oy-2),pixel(ox-2,oy-1),pixel(ox-1,oy-1),pixel(ox,oy-1),pixel(ox-2,oy),pixel(ox-1,oy),pixel(ox,oy)}) $fatal(1,"window neighborhood wrong (%0d,%0d)",ox,oy);
    checks++;
   end
  end
 endtask
 initial begin
  repeat(3) @(negedge clk);reset=0;
  for(epoch=0;epoch<3;epoch++) begin
   for(integer yy=0;yy<6;yy++) for(integer xx=0;xx<8;xx++) begin
    repeat($urandom_range(0,3)) step(0,0,xx,yy);
    repeat($urandom_range(0,2)) step(1,0,xx,yy);
    step(1,1,xx,yy);
   end
   repeat(4) step(1,0,0,0);
   reset=1;repeat(2) @(negedge clk);reset=0;
  end
  if(checks!=72)$fatal(1,"window count %0d",checks);
  $display("PASS WINDOW: all 72 interior neighborhoods across 3 frames, random CE/valid gaps, reset and stale RAM masking");$finish;
 end
endmodule
