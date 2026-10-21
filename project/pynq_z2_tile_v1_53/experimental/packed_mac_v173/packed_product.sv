// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Isolated arithmetic prototype, NOT integrated into the deployed detector.
// One signed 25x18 product gives two INT8 products with a common activation,
// or one full-width squared difference for normal-codebook search.
module packed_product(
 input wire clk,resetn,nearest,
 input wire signed [7:0] activation,weight_low,weight_high,
 input wire signed [17:0] difference,
 output reg nearest_out=0,
 (* USE_DSP="NO" *) output reg signed [17:0] product_low=0,
 (* USE_DSP="NO" *) output reg signed [17:0] product_high=0,
 output reg [34:0] squared_difference=0
);
 reg signed [24:0] operand_a=0;
 reg signed [17:0] operand_b=0;
 (* USE_DSP="YES" *) reg signed [42:0] product=0;
 reg mode0=0,mode1=0,negative0=0,negative1=0;
 reg signed [7:0] activation0=0,activation1=0;
 wire signed [16:0] raw_low=product[16:0];
 wire signed [25:0] raw_high=product>>>17;
 wire signed [17:0] correction=$signed({activation1,8'b0});
 always @(posedge clk)begin
  if(!resetn)begin
   operand_a<=0;operand_b<=0;product<=0;
   mode0<=0;mode1<=0;nearest_out<=0;negative0<=0;negative1<=0;
   activation0<=0;activation1<=0;product_low<=0;product_high<=0;squared_difference<=0;
  end else begin
   operand_a<=nearest?$signed(difference):$signed({weight_high,17'b0})+$signed({17'b0,weight_low});
   operand_b<=nearest?difference:activation;
   product<=operand_a*operand_b;
   activation0<=activation;activation1<=activation0;
   negative0<=weight_low[7];negative1<=negative0;
   mode0<=nearest;mode1<=mode0;nearest_out<=mode1;
   product_low<=mode1?18'sd0:$signed(raw_low)-(negative1?correction:18'sd0);
   product_high<=mode1?18'sd0:raw_high+(raw_low<0?26'sd1:26'sd0);
   squared_difference<=mode1?product[34:0]:35'd0;
  end
 end
endmodule
