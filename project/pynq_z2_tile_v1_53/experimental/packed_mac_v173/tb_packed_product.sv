`timescale 1ns/1ps
module tb_packed_product;
 reg clk=0;always #5 clk=~clk;
 reg resetn=0,nearest=0;
 reg signed [7:0] activation=0,weight_low=0,weight_high=0;
 reg signed [17:0] difference=0;
 wire nearest_out;wire signed [17:0] product_low,product_high;wire [34:0] squared_difference;
 packed_product dut(.*);
 reg signed [17:0] low0=0,low1=0,low2=0,high0=0,high1=0,high2=0;
 reg [34:0] square0=0,square1=0,square2=0;reg mode0=0,mode1=0,mode2=0;
 reg signed [63:0] d;integer checked=0,cycles=0,i,seed=173;
 always @(posedge clk)begin
  if(!resetn)begin cycles=0;low0=0;low1=0;low2=0;high0=0;high1=0;high2=0;square0=0;square1=0;square2=0;mode0=0;mode1=0;mode2=0;end
  else begin
   cycles=cycles+1;
   low2=low1;low1=low0;low0=nearest?0:activation*weight_low;
   high2=high1;high1=high0;high0=nearest?0:activation*weight_high;
   square2=square1;square1=square0;d=difference;square0=nearest?d*d:0;
   mode2=mode1;mode1=mode0;mode0=nearest;
   #1;
   if(cycles>3)begin
    if(nearest_out!==mode2||product_low!==low2||product_high!==high2||squared_difference!==square2)
     $fatal(1,"Packed DSP mismatch low=%0d/%0d high=%0d/%0d square=%0d/%0d",product_low,low2,product_high,high2,squared_difference,square2);
    checked=checked+1;
   end
  end
 end
 initial begin
  repeat(5)@(negedge clk);resetn=1;
  for(i=0;i<20000;i=i+1)begin
   @(negedge clk);nearest=i[0];activation=$random(seed);weight_low=$random(seed);weight_high=$random(seed);difference=$random(seed);
   if(i<512)begin activation=i[7:0];weight_low=8'sh80;weight_high=8'sh80;difference=18'sh20000;end
   if(i>=512&&i<1024)begin activation=i[7:0];weight_low=8'shff;weight_high=8'sh7f;difference=18'sh1ffff;end
  end
  repeat(5)@(negedge clk);
  $display("PACKED_DSP_SIGNED_INT8_AND_NEAREST_MODE_SWITCH_RTL_PASS checked=%0d",checked);$finish;
 end
 initial begin #1000000;$fatal(1,"Packed DSP watchdog");end
endmodule
