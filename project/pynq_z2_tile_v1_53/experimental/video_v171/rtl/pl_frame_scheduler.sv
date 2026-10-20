// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// PL ownership handoff: capture commit -> HLS start -> HLS done -> next capture.
// PS may configure the HLS addresses/model while owner=0, but MUST NOT read
// ap_ctrl or start HLS while this scheduler owns it (done is clear-on-read).
module pl_frame_scheduler #(
 parameter logic [31:0] HLS_BASE=32'h43c10000,
 parameter integer POLL_CYCLES=1000,REARM_CYCLES=32
)(
 input wire clk,resetn,enable,
 // All capture inputs have already crossed into clk. Commit must follow the
 // last successful DDR write RESPONSE, not just the final incoming video beat.
 input wire capture_commit,capture_invalid,
 input wire [31:0] capture_sequence,capture_crc,
 output logic capture_request_toggle=0,
 output wire owner,
 output logic result_publish=0,
 output logic [31:0] completed=0,rejected=0,last_sequence=0,last_crc=0,fault=0,
 output wire [31:0] m_axi_awaddr,output wire [2:0] m_axi_awprot,
 output wire m_axi_awvalid,input wire m_axi_awready,
 output wire [31:0] m_axi_wdata,output wire [3:0] m_axi_wstrb,
 output wire m_axi_wvalid,input wire m_axi_wready,
 input wire [1:0] m_axi_bresp,input wire m_axi_bvalid,output wire m_axi_bready,
 output wire [31:0] m_axi_araddr,output wire [2:0] m_axi_arprot,
 output wire m_axi_arvalid,input wire m_axi_arready,
 input wire [31:0] m_axi_rdata,input wire [1:0] m_axi_rresp,
 input wire m_axi_rvalid,output wire m_axi_rready,
 output wire capture_active
);
 localparam OFF=0,ARM=1,CAPTURE=2,WRITE=3,DELAY=4,READ_REQ=5,READ_DATA=6,ERROR=7,REARM=8;
 logic [3:0] state=OFF;
 logic aw_sent=0,w_sent=0;
 logic [31:0] delay_count=0,pending_sequence=0,pending_crc=0;
 assign owner=state!=OFF;
 assign capture_active=state==CAPTURE;
 assign m_axi_awaddr=HLS_BASE;assign m_axi_awprot=0;
 assign m_axi_awvalid=state==WRITE&&!aw_sent;
 assign m_axi_wdata=32'h1;assign m_axi_wstrb=4'hf;
 assign m_axi_wvalid=state==WRITE&&!w_sent;
 assign m_axi_bready=state==WRITE&&aw_sent&&w_sent;
 assign m_axi_araddr=HLS_BASE;assign m_axi_arprot=0;
 assign m_axi_arvalid=state==READ_REQ;
 assign m_axi_rready=state==READ_DATA;
 always @(posedge clk)begin
  result_publish<=0;
  if(!resetn)begin
   state<=OFF;capture_request_toggle<=0;completed<=0;rejected<=0;
   last_sequence<=0;last_crc<=0;fault<=0;aw_sent<=0;w_sent<=0;delay_count<=0;
   pending_sequence<=0;pending_crc<=0;
  end else case(state)
   OFF:if(enable)begin fault<=0;state<=REARM;delay_count<=REARM_CYCLES;end
   REARM:if(!enable)state<=OFF;else if(delay_count==0)state<=ARM;else delay_count<=delay_count-1;
   ARM:if(enable)begin capture_request_toggle<=~capture_request_toggle;state<=CAPTURE;end else state<=OFF;
   CAPTURE:if(capture_commit)begin
    if(capture_invalid)begin rejected<=rejected+1;state<=enable?REARM:OFF;delay_count<=REARM_CYCLES;end
    else begin pending_sequence<=capture_sequence;pending_crc<=capture_crc;aw_sent<=0;w_sent<=0;state<=WRITE;end
   end
   WRITE:begin
    if(m_axi_awvalid&&m_axi_awready)aw_sent<=1;
    if(m_axi_wvalid&&m_axi_wready)w_sent<=1;
    if(m_axi_bvalid&&m_axi_bready)begin
     if(m_axi_bresp!=0)begin fault<=32'h1;state<=ERROR;end
     else begin delay_count<=POLL_CYCLES;state<=DELAY;end
    end
   end
   DELAY:if(delay_count==0)state<=READ_REQ;else delay_count<=delay_count-1;
   READ_REQ:if(m_axi_arready)state<=READ_DATA;
   READ_DATA:if(m_axi_rvalid)begin
    if(m_axi_rresp!=0)begin fault<=32'h2;state<=ERROR;end
    else if(m_axi_rdata[1])begin
     completed<=completed+1;last_sequence<=pending_sequence;last_crc<=pending_crc;
     result_publish<=1;state<=enable?REARM:OFF;delay_count<=REARM_CYCLES;
    end else begin delay_count<=POLL_CYCLES;state<=DELAY;end
   end
   ERROR:if(!enable)state<=OFF;
   default:begin fault<=32'h3;state<=ERROR;end
  endcase
 end
endmodule
