`timescale 1ns/1ps
module tb_config_bridge;
 reg cc=0,pc=0,run=1;always #2.5 cc=~cc;always #6.734 if(run)pc=~pc;
 reg [31:0] c=0,lo=0,hi=0;wire [95:0] result;
 config_bridge dut(cc,pc,c,lo,hi,result);
 task settle;repeat(60)@(posedge cc);endtask
 initial begin
  settle();lo=32'h01230045;hi=32'h02340123;c=32'h80016406;settle();
  if(result!=={hi,lo,c})$fatal(1,"First committed bundle mismatch");
  lo=32'haaaa5555;hi=32'hffff0000;settle();
  if(result!==96'h02340123_01230045_80016406)$fatal(1,"Uncommitted ROI leaked");
  c=32'h00106407;settle();if(result!=={hi,lo,c})$fatal(1,"Second commit mismatch");
  // Destination clock loss while command arrives: immutable payload waits safely.
  @(negedge pc);run=0;lo=5;hi=20;c=32'h80003204;settle();
  lo=8;hi=40;settle();run=1;settle();
  if(result!==96'h00000014_00000005_80003204)$fatal(1,"Payload changed while handshake waited");
  c=32'h00003304;settle();if(result!=={hi,lo,c})$fatal(1,"Clock recovery failed");
  $display("PASS CONFIG: atomic commit, no uncommitted ROI leak, immutable pending payload, stopped-pixel-clock recovery");$finish;
 end
endmodule
