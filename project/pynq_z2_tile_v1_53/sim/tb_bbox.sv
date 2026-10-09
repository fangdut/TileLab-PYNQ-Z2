`timescale 1ns/1ps
module tb_bbox;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,de=0,vs=0,mask=0,en=1;reg[31:0]cfg=1;wire[23:0]rgb;
 bbox_overlay #(.WIDTH(8),.HEIGHT(6)) dut(clk,reset,de,vs,mask,en,cfg,24'h112233,rgb);
 task tick(input bit d,v,m,input bit yellow);
  @(negedge clk);de=d;vs=v;mask=m;#1;
  if(rgb!==(yellow?24'hff0000:24'h112233))$fatal(1,"box x=%0d y=%0d got=%h expectedyellow=%d",dut.x,dut.y,rgb,yellow);
  @(posedge clk);#1;
 endtask
 task frame(input integer kind,oldkind,rows);
  tick(0,1,0,0);tick(0,0,0,0);
  for(integer y=0;y<rows;y++)begin
   for(integer x=0;x<8;x++)begin
    tick(1,0,kind==1?(x>=1&&x<=3&&y>=1&&y<=3):kind==2?(x==7&&y==5):0,
       oldkind==1?(((x==1||x==3)&&y>=1&&y<=3)||((y==1||y==3)&&x>=1&&x<=3)):oldkind==2?(x==7&&y==5):0);
   end
   tick(0,0,0,0);
  end
 endtask
 initial begin
  repeat(30)@(negedge clk);reset=0;
  frame(1,0,6);frame(2,1,6);frame(0,2,6);frame(1,0,6);
  cfg=2;frame(1,0,6);frame(1,1,3);frame(1,0,6);
  reset=1;repeat(2)@(negedge clk);reset=0;frame(1,0,6);
  en=0;frame(1,0,6);
  $display("PASS BBOX: previous frame, moving box, empty, config invalidation, partial frame, reset, disabled");$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
