// SPDX-License-Identifier: MIT
// Native six-enabled-clock shared MAC. Experimental, not board accepted.
`timescale 1ns/1ps
module shared_mac(
 input wire ap_clk,ap_rst,ap_ce,nearest,
 input wire[63:0] activations,
 input wire[1023:0] centers0,centers1,query_bits,
 output wire[959:0] ap_return
);
 reg[5:0] mode=0;
 always @(posedge ap_clk)begin
  if(ap_rst)mode<=0;
  else if(ap_ce)mode<={mode[4:0],nearest};
 end
 genvar lane,j;
 generate for(lane=0;lane<16;lane=lane+1)begin: lanes
  wire signed[39:0] low[0:7];wire signed[19:0] high[0:7];
  for(j=0;j<8;j=j+1)begin: products
   localparam D=(lane%8)*8+j;
   wire signed[15:0] query_value=query_bits[D*16+:16];
   wire signed[15:0] center_value=(lane<8)?centers0[(D%16)*64+(D/16)*16+:16]:centers1[(D%16)*64+(D/16)*16+:16];
   wire signed[16:0] difference={query_value[15],query_value}-{center_value[15],center_value};
   wire signed[7:0] activation=activations[j*8+:8];
   wire signed[7:0] w0=centers0[lane*64+j*8+:8],w1=centers1[lane*64+j*8+:8];
   wire signed[24:0] upper_weight={w1[7],w1,16'b0};
   wire signed[24:0] lower_weight={{17{w0[7]}},w0};
   reg signed[24:0] operand_a;
   reg signed[17:0] operand_b;
   (* use_dsp="yes" *) reg signed[42:0] product;
   reg signed[39:0] decoded_low;
   reg signed[19:0] decoded_high;
   always @(posedge ap_clk)if(ap_ce)begin
    operand_a<=nearest?{{8{difference[16]}},difference}:upper_weight+lower_weight;
    operand_b<=nearest?{difference[16],difference}:{{10{activation[7]}},activation};
    product<=operand_a*operand_b;
    decoded_low<=mode[1]?{6'b0,product[33:0]}:{{24{product[15]}},product[15:0]};
    decoded_high<=$signed(product[31:16])+$signed({15'b0,product[15]});
   end
   assign low[j]=decoded_low;assign high[j]=decoded_high;
  end
  reg signed[39:0] pair_lo[0:3],quad_lo[0:1],sum_lo;
  reg signed[19:0] pair_hi[0:3],quad_hi[0:1],sum_hi;
  integer p;
  always @(posedge ap_clk)if(ap_ce)begin
   for(p=0;p<4;p=p+1)begin pair_lo[p]<=low[p*2]+low[p*2+1];pair_hi[p]<=high[p*2]+high[p*2+1];end
   for(p=0;p<2;p=p+1)begin quad_lo[p]<=pair_lo[p*2]+pair_lo[p*2+1];quad_hi[p]<=pair_hi[p*2]+pair_hi[p*2+1];end
   sum_lo<=quad_lo[0]+quad_lo[1];sum_hi<=quad_hi[0]+quad_hi[1];
  end
  assign ap_return[lane*40+:40]=sum_lo;
  assign ap_return[640+lane*20+:20]=mode[5]?20'b0:sum_hi;
 end endgenerate
endmodule
