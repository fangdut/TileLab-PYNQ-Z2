// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Capture and inference have independent state machines. Only PL changes the
// input pointer and starts HLS. A granted job drains even if enable falls.
module pl_frame_scheduler_overlap #(
 parameter logic [31:0] HLS_BASE=32'h43c10000,
 parameter integer POLL_CYCLES=1000,REARM_CYCLES=32
)(
 input wire clk,resetn,enable,
 input wire capture_commit,capture_invalid,
 input wire [31:0] capture_sequence,capture_crc,
 output wire capture_active,owner,
 output wire [31:0] capture_base,last_input_base,
 output logic result_publish=0,start_pulse=0,
 output wire [31:0] completed,rejected,last_sequence,last_crc,dropped,fault,
 output wire [31:0] m_axi_awaddr,output wire [2:0] m_axi_awprot,
 output wire m_axi_awvalid,input wire m_axi_awready,
 output wire [31:0] m_axi_wdata,output wire [3:0] m_axi_wstrb,
 output wire m_axi_wvalid,input wire m_axi_wready,
 input wire [1:0] m_axi_bresp,input wire m_axi_bvalid,output wire m_axi_bready,
 output wire [31:0] m_axi_araddr,output wire [2:0] m_axi_arprot,
 output wire m_axi_arvalid,input wire m_axi_arready,
 input wire [31:0] m_axi_rdata,input wire [1:0] m_axi_rresp,
 input wire m_axi_rvalid,output wire m_axi_rready,
 input wire result_done,result_error
);
 localparam C_OFF=0,C_REARM=1,C_ARM=2,C_ACTIVE=3;
 localparam I_IDLE=0,I_POINTER=1,I_START=2,I_DELAY=3,I_READ_REQ=4,I_READ_DATA=5,I_RESULT=6,I_ERROR=7;
 logic [1:0] cstate=C_OFF;
 logic [2:0] istate=I_IDLE;
 logic [31:0] rearm=0,poll_count=0,bus_fault=0;
 logic aw_sent=0,w_sent=0;
 wire cg,ig,cbusy,ibusy,available,result_commit,last_valid,drained;
 wire [31:0] input_base,input_sequence,input_crc,queue_fault;
 wire run=enable&&fault==0;
 wire done_to_queue=istate==I_RESULT&&result_done&&!result_error;
 assign capture_active=cstate==C_ACTIVE;
 assign owner=enable||cbusy||ibusy||available;
 assign fault=bus_fault|(queue_fault<<16);
 frame_slot_queue slots(
  .clk(clk),.resetn(resetn),.enable(run),
  .capture_acquire(cstate==C_ARM&&run),
  .capture_commit(capture_commit&&capture_active),.capture_invalid(capture_invalid),
  .capture_sequence(capture_sequence),.capture_crc(capture_crc),
  .capture_grant(cg),.capture_base(capture_base),.capture_busy(cbusy),
  .infer_acquire(istate==I_IDLE&&run),.infer_done(done_to_queue),
  .infer_grant(ig),.infer_base(input_base),.infer_sequence(input_sequence),.infer_crc(input_crc),
  .infer_busy(ibusy),.ready_available(available),.result_commit(result_commit),
  .last_base(last_input_base),.last_sequence(last_sequence),.last_crc(last_crc),
  .last_valid(last_valid),.drained(drained),.completed(completed),.rejected(rejected),.dropped(dropped),.fault(queue_fault));
 wire writing=istate==I_POINTER||istate==I_START;
 assign m_axi_awaddr=istate==I_POINTER?HLS_BASE+32'h28:HLS_BASE;
 assign m_axi_awprot=0;
 assign m_axi_awvalid=writing&&!aw_sent;
 assign m_axi_wdata=istate==I_POINTER?input_base:32'h1;
 assign m_axi_wstrb=4'hf;
 assign m_axi_wvalid=writing&&!w_sent;
 assign m_axi_bready=writing&&aw_sent&&w_sent;
 assign m_axi_araddr=HLS_BASE;
 assign m_axi_arprot=0;
 assign m_axi_arvalid=istate==I_READ_REQ;
 assign m_axi_rready=istate==I_READ_DATA;
 always @(posedge clk)begin
  result_publish<=0;start_pulse<=0;
  if(!resetn)begin
   cstate<=C_OFF;istate<=I_IDLE;rearm<=0;poll_count<=0;
   aw_sent<=0;w_sent<=0;bus_fault<=0;
  end else begin
   bus_fault<=bus_fault|(capture_commit&&!capture_active?32'h10:32'h0)
    |(writing&&m_axi_bvalid&&m_axi_bready&&m_axi_bresp!=0?32'h1:32'h0)
    |(istate==I_READ_DATA&&m_axi_rvalid&&m_axi_rresp!=0?32'h2:32'h0)
    |(istate==I_RESULT&&result_done&&result_error?32'h4:32'h0);
   case(cstate)
    C_OFF:if(run)begin cstate<=C_REARM;rearm<=REARM_CYCLES;end
    C_REARM:if(!run)cstate<=C_OFF;else if(rearm==0)cstate<=C_ARM;else rearm<=rearm-1;
    // Grant wins over disable: this slot was already reserved and must drain.
    C_ARM:if(cg)cstate<=C_ACTIVE;else if(!run)cstate<=C_OFF;
    C_ACTIVE:if(capture_commit)begin cstate<=run?C_REARM:C_OFF;rearm<=REARM_CYCLES;end
   endcase
   case(istate)
    I_IDLE:if(ig)begin istate<=I_POINTER;aw_sent<=0;w_sent<=0;end
    I_POINTER,I_START:begin
     if(m_axi_awvalid&&m_axi_awready)aw_sent<=1;
     if(m_axi_wvalid&&m_axi_wready)w_sent<=1;
     if(m_axi_bvalid&&m_axi_bready)begin
      aw_sent<=0;w_sent<=0;
      if(m_axi_bresp!=0)istate<=I_ERROR;
      else if(istate==I_POINTER)istate<=I_START;
      else begin start_pulse<=1;poll_count<=POLL_CYCLES;istate<=I_DELAY;end
     end
    end
    I_DELAY:if(poll_count==0)istate<=I_READ_REQ;else poll_count<=poll_count-1;
    I_READ_REQ:if(m_axi_arready)istate<=I_READ_DATA;
    I_READ_DATA:if(m_axi_rvalid)begin
     if(m_axi_rresp!=0)istate<=I_ERROR;
     else if(m_axi_rdata[1])begin result_publish<=1;istate<=I_RESULT;end
     else begin poll_count<=POLL_CYCLES;istate<=I_DELAY;end
    end
    I_RESULT:if(result_done)begin
     if(result_error)istate<=I_ERROR;
     else istate<=I_IDLE;
    end
    I_ERROR:begin end // Reserved input remains protected until system reset.
   endcase
  end
 end
endmodule
