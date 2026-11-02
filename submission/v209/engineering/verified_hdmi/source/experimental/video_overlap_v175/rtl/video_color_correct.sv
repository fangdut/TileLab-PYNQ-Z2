// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Startup black/white calibration coefficients, never CPU pixel processing.
// A handshake transfers all six coefficients atomically. New capture waits
// for the latest transfer to finish; live-owner CSR writes are rejected.
module video_color_correct(
 input wire control_clk,control_resetn,pixel_clk,pixel_resetn,
 input wire [31:0] config_r,config_g,config_b,input wire config_changed,
 output reg config_ready=0,
 input wire [23:0] rgb,input wire de,vs,
 output reg [23:0] rgb_out=0,output reg de_out=0,vs_out=0
);
 localparam [53:0] IDENTITY={8'd0,10'd256,8'd0,10'd256,8'd0,10'd256};
 localparam IDLE=0,WAIT_ACK=1,WAIT_CLEAR=2,DRAIN=3;
 reg [1:0] state=DRAIN;reg [5:0] drain=32;
 reg dirty=1,send=0;reg [53:0] transfer=IDENTITY;
 wire received,dest_request;wire [53:0] dest_data;
 always @(posedge control_clk)begin
  if(!control_resetn)begin state<=DRAIN;drain<=32;dirty<=1;send<=0;transfer<=IDENTITY;config_ready<=0;end
  else begin
   case(state)
    DRAIN:if(drain!=0)drain<=drain-1;else if(!received)state<=IDLE;
    IDLE:if(dirty)begin
     transfer<={config_b[23:16],config_b[9:0],config_g[23:16],config_g[9:0],config_r[23:16],config_r[9:0]};
     send<=1;dirty<=0;config_ready<=0;state<=WAIT_ACK;
    end
    WAIT_ACK:if(received)begin send<=0;state<=WAIT_CLEAR;end
    WAIT_CLEAR:if(!received)begin state<=IDLE;if(!dirty&&!config_changed)config_ready<=1;end
   endcase
   if(config_changed)begin dirty<=1;config_ready<=0;end
  end
 end
 xpm_cdc_handshake #(.WIDTH(54),.DEST_EXT_HSK(0),.DEST_SYNC_FF(3),.SRC_SYNC_FF(3),.INIT_SYNC_FF(1),.SIM_ASSERT_CHK(1)) config_bridge(
  .src_clk(control_clk),.src_in(transfer),.src_send(send),.src_rcv(received),
  .dest_clk(pixel_clk),.dest_out(dest_data),.dest_req(dest_request),.dest_ack(1'b0));
 // Retain coefficients across HDMI clock loss. Only data/DE/VS are reset by
 // capture reset. FPGA initialization and the control-side startup transfer
 // both select identity, including after a global control reset.
 reg [9:0] gain_r=256,gain_g=256,gain_b=256;
 reg [7:0] black_r=0,black_g=0,black_b=0;
 always @(posedge pixel_clk)if(dest_request)begin
  gain_r<=dest_data[9:0];black_r<=dest_data[17:10];
  gain_g<=dest_data[27:18];black_g<=dest_data[35:28];
  gain_b<=dest_data[45:36];black_b<=dest_data[53:46];
 end
 wire [7:0] r=rgb[23:16]>black_r?rgb[23:16]-black_r:8'd0;
 wire [7:0] g=rgb[15:8]>black_g?rgb[15:8]-black_g:8'd0;
 wire [7:0] b=rgb[7:0]>black_b?rgb[7:0]-black_b:8'd0;
 (* USE_DSP="NO" *) reg [17:0] product_r=0,product_g=0,product_b=0;
 reg de_pipe=0,vs_pipe=0;
 function automatic [7:0] rounded_clip(input [17:0] value);
  reg [18:0] sum;
  begin sum={1'b0,value}+19'd128;rounded_clip=sum[18:8]>255?8'd255:sum[15:8];end
 endfunction
 always @(posedge pixel_clk)begin
  if(!pixel_resetn)begin
   product_r<=0;product_g<=0;product_b<=0;de_pipe<=0;vs_pipe<=0;
   rgb_out<=0;de_out<=0;vs_out<=0;
  end else begin
   product_r<=r*gain_r;product_g<=g*gain_g;product_b<=b*gain_b;
   de_pipe<=de;vs_pipe<=vs;
   rgb_out<={rounded_clip(product_r),rounded_clip(product_g),rounded_clip(product_b)};
   de_out<=de_pipe;vs_out<=vs_pipe;
  end
 end
endmodule
