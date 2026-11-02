// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Whole-tile classification indicator, not a pixel-accurate crack overlay.
module video_alarm_border(
 input wire pixel_clk,resetn,alarm,valid,
 input wire [23:0] rgb_in,input wire de_in,hs_in,vs_in,
 output reg [23:0] rgb_out=0,output reg de_out=0,hs_out=0,vs_out=0
);
 (* ASYNC_REG="TRUE" *) reg [2:0] alarm_sync=0,valid_sync=0;
 reg old_de=0,old_vs=0;reg [11:0] x=0,y=0;
 wire border=x>=280&&x<1000&&y<720&&(x<288||x>=992||y<8||y>=712);
 always @(posedge pixel_clk)begin
  if(!resetn)begin
   alarm_sync<=0;valid_sync<=0;old_de<=0;old_vs<=0;x<=0;y<=0;
   rgb_out<=0;de_out<=0;hs_out<=0;vs_out<=0;
  end else begin
   alarm_sync<={alarm_sync[1:0],alarm};valid_sync<={valid_sync[1:0],valid};
   old_de<=de_in;old_vs<=vs_in;
   if(vs_in&&!old_vs)begin x<=0;y<=0;end
   else if(de_in)x<=x+1;
   else if(old_de)begin x<=0;y<=y+1;end
   rgb_out<=de_in&&border&&valid_sync[2]?(alarm_sync[2]?24'hff0000:24'h0000ff):rgb_in;
   de_out<=de_in;hs_out<=hs_in;vs_out<=vs_in;
  end
 end
endmodule
