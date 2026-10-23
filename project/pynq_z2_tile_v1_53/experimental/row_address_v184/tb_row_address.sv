`timescale 1ns/1ps
module tb_row_address;
 reg ap_clk=0;always #4 ap_clk=~ap_clk;
 reg ap_rst=0,ap_ce=1,feed_valid=0;reg [9:0] row=0;reg [10:0] width=1;
 wire [20:0] ap_return;
 texture_integer_row_offset dut(.*);
 reg [20:0] expected[0:3];reg [3:0] valid_pipe=0;integer checked=0;
 always @(posedge ap_clk)begin
  expected[0]<=32'(row)*32'(width);
  for(integer k=1;k<4;k=k+1)expected[k]<=expected[k-1];
  valid_pipe<={valid_pipe[2:0],feed_valid};
  #1;if(valid_pipe[3])begin
   if(ap_return!==expected[3])$fatal(1,"Generated row helper output/latency mismatch %h/%h",ap_return,expected[3]);
   checked=checked+1;
  end
 end
 // Independently check the generated DSP operation under enable stalls.
 reg ce=0;reg [10:0] a=0;reg [9:0] b=0;wire [20:0] product;
 texture_integer_mul_11ns_10ns_21_4_0 #(.din0_WIDTH(11),.din1_WIDTH(10),.dout_WIDTH(21))
  mul(.clk(ap_clk),.ce(ce),.reset(ap_rst),.din0(a),.din1(b),.dout(product));
 reg [20:0] m_expected[0:2];reg [2:0] m_valid=0;reg [20:0] held;integer m_checked=0,stalls=0;
 always @(posedge ap_clk)begin
  held=product;
  if(ce)begin
   m_expected[0]<=32'(a)*32'(b);m_expected[1]<=m_expected[0];m_expected[2]<=m_expected[1];
   m_valid<={m_valid[1:0],1'b1};
  end
  #1;if(m_valid[2])begin
   if(product!==m_expected[2])$fatal(1,"Generated multiplier enable pipeline mismatch");
   m_checked=m_checked+1;
   if(!ce)begin if(product!==held)$fatal(1,"Multiplier changed during stall");stalls=stalls+1;end
  end
 end
 reg [31:0] rng=32'h184ac901;
 function [31:0] random32();begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);random32=rng;end endfunction
 integer i;
 initial begin
  for(i=0;i<1048576;i=i+1)begin
   @(negedge ap_clk);row=i>>10;width=(i&1023)+1;feed_valid=1;
   ce=(random32()%3)!=0;a=(random32()%1024)+1;b=random32();
  end
  @(negedge ap_clk);feed_valid=0;ce=0;repeat(5)@(negedge ap_clk);
  if(checked!=1048576||m_checked<1000000||stalls<300000)$fatal(1,"Insufficient RTL coverage");
  $display("ROW_ADDRESS_GENERATED_RTL_EXHAUSTIVE_AND_ENABLE_STALL_PASS checked=%0d multiplier_checks=%0d stalls=%0d",checked,m_checked,stalls);
  $finish;
 end
 initial begin #10000000;$fatal(1,"Watchdog");end
endmodule
