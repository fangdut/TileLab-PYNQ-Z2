`timescale 1ns/1ps
module tb_candidate_stats;
 reg clk=0,cc=0,cc_run=1;always #5 clk=~clk;always #3.5 if(cc_run)cc=~cc;
 reg reset=1,de=0,vs=0,mask=0;reg [31:0] cfg=32'h12345678;
 wire [31:0] n,lo,hi,seq,act,status,crc;
 candidate_stats #(.WIDTH(8),.HEIGHT(6)) dut(clk,cc,reset,de,vs,mask,cfg,n,lo,hi,seq,act,status,crc);
 task pulse_vs;
  @(negedge clk);vs=1;de=0;mask=0;repeat(3)@(negedge clk);vs=0;
 endtask
 task frame(input integer kind);
  for(integer y=0;y<6;y++)begin
   for(integer x=0;x<8;x++)begin
    @(negedge clk);de=1;
    mask=kind==1?(x==7 && y==5):kind==2?((x==0 && y==0)||(x==7 && y==5)):kind==3?1:kind==4?(x>=2 && x<=5 && y>=1 && y<=3):0;
   end
   @(negedge clk);de=0;mask=0;repeat(3)@(negedge clk);
  end
  pulse_vs();
 endtask
 task check(input integer es,en,el,eh,ec,input [31:0] expected_crc);
  repeat(80)@(negedge clk);
  if(crc!==expected_crc)$fatal(1,"CRC got=%h expected=%h",crc,expected_crc);
  if({seq,n,lo,hi,act,status}!=={32'(es),32'(en),32'(el),32'(eh),32'(ec),(en?32'd3:32'd1)})
   $fatal(1,"stats seq=%d n=%d lo=%h hi=%h cfg=%h status=%d",seq,n,lo,hi,act,status);
 endtask
 initial begin
  repeat(30)@(negedge clk);reset=0;pulse_vs();
  frame(0);check(1,0,0,0,cfg,32'hb1c2a1a3);
  frame(1);check(2,1,32'h00050007,32'h00050007,cfg,32'h5c7a2283);
  frame(2);check(3,2,0,32'h00050007,cfg,32'h9726f126);
  frame(3);check(4,48,0,32'h00050007,cfg,32'h41d9ed00);
  frame(4);check(5,12,32'h00010002,32'h00030005,cfg,32'h429fafc9);
  // Partial frame before reset must never leak or publish; sequence stays monotonic.
  @(negedge clk);de=1;mask=1;repeat(4)@(negedge clk);reset=1;de=0;mask=0;
  repeat(20)@(negedge clk);reset=0;cfg=32'h87654321;pulse_vs();frame(1);check(6,1,32'h00050007,32'h00050007,cfg,32'h5c7a2283);
  // Stop destination clock for several full frames; eventual latest snapshot remains atomic.
  cc_run=0;frame(3);frame(0);frame(4);cc_run=1;check(9,12,32'h00010002,32'h00030005,cfg,32'h429fafc9);
  $display("PASS CANDIDATE: empty, last pixel, disjoint corners, full, rectangle, reset partial frame, stopped control clock, atomic latest snapshot");$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
