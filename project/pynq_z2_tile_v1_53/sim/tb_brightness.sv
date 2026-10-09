`timescale 1ns/1ps
module tb_brightness;
 reg clk=0,cc=0,cc_run=1;always #5 clk=~clk;always #3.5 if(cc_run)cc=~cc;
 reg reset=1,de=0,vs=0,include_pixel=0;reg [7:0] gray=0;
 reg [31:0] cfg=32'h12345678,rmin=32'h00010002,rmax=32'h00040006;
 wire [31:0] n,s,seq,act,lo,hi;
 brightness_stats #(.WIDTH(8),.HEIGHT(6)) dut(clk,cc,reset,de,vs,include_pixel,gray,cfg,rmin,rmax,n,s,seq,act,lo,hi);
 task pulse_vs;@(negedge clk);vs=1;de=0;repeat(3)@(negedge clk);vs=0;endtask
 task frame(input integer kind);
  for(integer y=0;y<6;y++)begin
   for(integer x=0;x<8;x++)begin
    @(negedge clk);de=1;gray=kind==3?255:y*8+x;
    include_pixel=kind==0?0:kind==1?(x==7 && y==5):kind==2?(x>=2 && x<=6 && y>=1 && y<=4):1;
   end
   @(negedge clk);de=0;repeat(3)@(negedge clk);
  end
  pulse_vs();
 endtask
 task check(input integer es,en,et);
  repeat(80)@(negedge clk);
  if({seq,n,s,act,lo,hi}!=={32'(es),32'(en),32'(et),cfg,rmin,rmax})$fatal(1,"brightness seq=%d n=%d sum=%d cfg=%h",seq,n,s,act);
 endtask
 initial begin
  repeat(30)@(negedge clk);reset=0;pulse_vs();
  frame(0);check(1,0,0);frame(1);check(2,1,47);frame(2);check(3,20,480);frame(3);check(4,48,12240);
  @(negedge clk);de=1;include_pixel=1;gray=255;repeat(4)@(negedge clk);reset=1;de=0;
  repeat(20)@(negedge clk);reset=0;cfg=32'h87654321;pulse_vs();frame(1);check(5,1,47);
  cc_run=0;frame(3);frame(0);frame(2);cc_run=1;check(8,20,480);
  $display("PASS BRIGHTNESS UNIT: empty last-pixel ROI full-white reset-partial stopped-control atomic-latest");$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
