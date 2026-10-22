// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Give DDC its control/reference clock before inviting the source to read EDID.
// Independent of PixelClk lock: the source may wait for HPD before sending video.
module hdmi_hpd_startup #(
 parameter integer STARTUP_CYCLES=20000000,
 parameter integer COUNTER_BITS=$clog2(STARTUP_CYCLES+1)
)(input wire clk,resetn,output reg hpd=0);
 reg [COUNTER_BITS-1:0] counter=0;
 always @(posedge clk or negedge resetn)begin
  if(!resetn)begin counter<=0;hpd<=0;end
  else if(!hpd)begin
   if(counter==STARTUP_CYCLES-1)hpd<=1;
   else counter<=counter+1;
  end
 end
endmodule
