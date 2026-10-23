// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Read the completed HLS header in PL. Software does not decide the alarm.
// The scheduler must keep capture disabled until done, including on errors.
module pl_result_latch_reference_v176 #(
 parameter logic [31:0] BASE=32'h07000000,
 parameter integer PIXELS=720*720,GRID=28,TASKS=47
)(
 input wire clk,resetn,request,
 output wire busy,output logic done=0,
 output logic [31:0] fault=0,frame_sequence=0,peak=0,threshold=0,mask_pixels=0,
 output logic alarm=0,valid=0,
 output wire [31:0] m_axi_araddr,output wire [7:0] m_axi_arlen,
 output wire [2:0] m_axi_arsize,output wire [1:0] m_axi_arburst,
 output wire m_axi_arvalid,input wire m_axi_arready,
 input wire [31:0] m_axi_rdata,input wire [1:0] m_axi_rresp,
 input wire m_axi_rlast,m_axi_rvalid,output wire m_axi_rready
);
 localparam IDLE=0,ADDR=1,DATA=2,CHECK=3;
 logic [1:0] state=IDLE;
 logic [31:0] header[0:9];logic [4:0] index=0;logic bad=0;
 assign busy=state!=IDLE;
 assign m_axi_araddr=BASE;assign m_axi_arlen=9;
 assign m_axi_arsize=2;assign m_axi_arburst=1;
 assign m_axi_arvalid=state==ADDR;
 assign m_axi_rready=state==DATA;
 wire malformed=header[0]!=32'h17000001||header[1]!=0||header[2]>1||
  header[2]!=(header[3]>header[4])||header[5]!=GRID||header[6]>PIXELS||
  header[7]!=PIXELS||header[8]!=TASKS||(valid&&header[9]!=frame_sequence+32'd1);
 always @(posedge clk)begin
  done<=0;
  if(!resetn)begin
   state<=IDLE;index<=0;bad<=0;fault<=0;frame_sequence<=0;
   peak<=0;threshold<=0;mask_pixels<=0;alarm<=0;valid<=0;
  end else begin
   if(request&&busy)fault<=32'h2;
   case(state)
    IDLE:if(request)begin state<=ADDR;index<=0;bad<=0;end
    ADDR:if(m_axi_arready)state<=DATA;
    DATA:if(m_axi_rvalid)begin
     if(index<10)header[index]<=m_axi_rdata;
     if(m_axi_rresp!=0||m_axi_rlast!=(index==9))bad<=1;
     if(index!=31)index<=index+1;
     if(m_axi_rlast)state<=CHECK;
    end
    CHECK:begin
     if(bad||malformed||fault!=0)begin fault<=bad?32'h4:32'h8;valid<=0;end
     else begin
      frame_sequence<=header[9];peak<=header[3];threshold<=header[4];
      mask_pixels<=header[6];alarm<=header[2][0];valid<=1;
     end
     done<=1;state<=IDLE;
    end
   endcase
  end
 end
endmodule
