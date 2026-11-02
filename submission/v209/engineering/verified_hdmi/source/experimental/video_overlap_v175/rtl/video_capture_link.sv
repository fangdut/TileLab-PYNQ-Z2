// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// AMD XPM implementation/terms are supplied by Vivado, not copied here.
module video_capture_link #(
 parameter integer FRAME_WIDTH=1280,FRAME_HEIGHT=720,
 parameter integer ROI_X=280,ROI_Y=0,ROI_WIDTH=720,ROI_HEIGHT=720,FIFO_DEPTH=2048
)(
 input wire pixel_clk,pixel_resetn,control_clk,control_resetn,capture_active,
 input wire [23:0] rgb,input wire de,vs,
 output wire [63:0] data,output wire [1:0] user,output wire valid,input wire ready,
 output wire producer_resetn
);
 // Assert even if PixelClk is stopped. Release synchronously to PixelClk;
 // keep the producer reset until XPM finishes its write-domain reset.
 (* ASYNC_REG="TRUE" *) reg [3:0] reset_pipe=4'hf;
 wire async_resetn=pixel_resetn&&control_resetn;
 always @(posedge pixel_clk or negedge async_resetn)
  if(!async_resetn)reset_pipe<=4'hf;
  else reset_pipe<={reset_pipe[2:0],1'b0};
 wire fifo_reset=reset_pipe[3];wire full,empty,wr_busy,rd_busy;
 wire [63:0] pdata;wire [1:0] puser;wire pvalid,pready;
 wire [65:0] dout;
 assign pready=!full&&!wr_busy;
 assign {user,data}=dout;
 assign valid=!empty&&!rd_busy&&control_resetn;
 assign producer_resetn=!fifo_reset&&!wr_busy;
 video_roi_tokens #(.FRAME_WIDTH(FRAME_WIDTH),.FRAME_HEIGHT(FRAME_HEIGHT),.ROI_X(ROI_X),.ROI_Y(ROI_Y),.ROI_WIDTH(ROI_WIDTH),.ROI_HEIGHT(ROI_HEIGHT)) producer(
  .pixel_clk(pixel_clk),.resetn(producer_resetn),.capture_active(capture_active),
  .rgb(rgb),.de(de),.vs(vs),.m_data(pdata),.m_user(puser),.m_valid(pvalid),.m_ready(pready));
 xpm_fifo_async #(.FIFO_MEMORY_TYPE("block"),.FIFO_WRITE_DEPTH(FIFO_DEPTH),
  .WRITE_DATA_WIDTH(66),.READ_DATA_WIDTH(66),.READ_MODE("fwft"),.FIFO_READ_LATENCY(0),
  .CDC_SYNC_STAGES(3),.RELATED_CLOCKS(0),.USE_ADV_FEATURES("0000"),.SIM_ASSERT_CHK(1),
  .WR_DATA_COUNT_WIDTH($clog2(FIFO_DEPTH)+1),.RD_DATA_COUNT_WIDTH($clog2(FIFO_DEPTH)+1),
  .PROG_FULL_THRESH(10),.PROG_EMPTY_THRESH(10),.DOUT_RESET_VALUE("0")) fifo(
  .sleep(1'b0),.rst(fifo_reset),.wr_clk(pixel_clk),.wr_en(pvalid&&pready),.din({puser,pdata}),
  .full(full),.wr_rst_busy(wr_busy),.rd_clk(control_clk),.rd_en(valid&&ready),.dout(dout),.empty(empty),.rd_rst_busy(rd_busy),
  .injectsbiterr(1'b0),.injectdbiterr(1'b0));
endmodule
