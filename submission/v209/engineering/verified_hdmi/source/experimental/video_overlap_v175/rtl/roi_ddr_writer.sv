// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Token stream, already in clk domain: user=1 SOF(sequence), user=0 two RGB32
// pixels, user=2 EOF({CRC32,sequence}), user=3 invalid EOF. Commit follows every
// DDR B response. One outstanding burst, independent AW/W handshakes.
module roi_ddr_writer #(
 parameter logic [31:0] BASE=32'h06000000,
 parameter integer EXPECTED_WORDS=259200
)(
 input wire clk,resetn,
 input wire [63:0] s_data,input wire [1:0] s_user,input wire s_valid,output wire s_ready,
 output logic commit=0,invalid=0,output logic [31:0] frame_sequence=0,crc=0,
 output wire [31:0] m_axi_awaddr,output wire [7:0] m_axi_awlen,
 output wire [2:0] m_axi_awsize,output wire [1:0] m_axi_awburst,
 output wire m_axi_awvalid,input wire m_axi_awready,
 output wire [63:0] m_axi_wdata,output wire [7:0] m_axi_wstrb,
 output wire m_axi_wlast,m_axi_wvalid,input wire m_axi_wready,
 input wire [1:0] m_axi_bresp,input wire m_axi_bvalid,output wire m_axi_bready,
 input wire [31:0] frame_base
);
 localparam FILL=0,SEND=1;
 logic state=FILL,started=0,bad=0,end_pending=0,aw_sent=0,data_sent=0;
 logic [63:0] buffer[0:15];logic [4:0] fill=0,burst=0,index=0;
 logic [31:0] address=BASE,words=0,frame_seq=0,crc_state=32'hffffffff;
 logic [31:0] end_crc=0,end_seq=0;
 assign s_ready=state==FILL;
 assign m_axi_awaddr=address;assign m_axi_awlen=burst-1;
 assign m_axi_awsize=3;assign m_axi_awburst=1;
 assign m_axi_awvalid=state==SEND&&!aw_sent;
 assign m_axi_wdata=buffer[index[3:0]];assign m_axi_wstrb=8'hff;
 assign m_axi_wlast=index==burst-1;
 assign m_axi_wvalid=state==SEND&&!data_sent;
 assign m_axi_bready=state==SEND&&aw_sent&&data_sent;
 function automatic [31:0] crc64(input [31:0] c0,input [63:0] d);
  reg [31:0] c;integer bit_index;begin
   c=c0;
   for(bit_index=0;bit_index<64;bit_index=bit_index+1)c=(c>>1)^({32{c[0]^d[bit_index]}}&32'hedb88320);
   crc64=c;
  end
 endfunction
 always @(posedge clk)begin
  commit<=0;
  if(!resetn)begin
   state<=FILL;started<=0;bad<=0;end_pending<=0;aw_sent<=0;data_sent<=0;
   fill<=0;burst<=0;index<=0;address<=BASE;words<=0;frame_seq<=0;crc_state<=32'hffffffff;
   invalid<=0;frame_sequence<=0;crc<=0;end_crc<=0;end_seq<=0;
  end else if(state==FILL)begin
   if(s_valid)case(s_user)
    1:begin
     // A new SOF safely replaces an interrupted partial frame. FILL has no
     // outstanding DDR writes; no completion is published for the old frame.
     started<=1;bad<=0;fill<=0;address<=frame_base;words<=0;frame_seq<=s_data[31:0];crc_state<=32'hffffffff;
    end
    0:begin
     if(!started)bad<=1;
     else begin
      crc_state<=crc64(crc_state,s_data);if(words!=32'hffffffff)words<=words+1;
      if(words>=EXPECTED_WORDS)bad<=1;
      else begin
       buffer[fill[3:0]]<=s_data;
       if(fill==15)begin state<=SEND;burst<=16;index<=0;aw_sent<=0;data_sent<=0;end_pending<=0;fill<=0;end
       else fill<=fill+1;
      end
     end
    end
    default:begin
     bad<=bad||!started||s_user==3||words!=EXPECTED_WORDS||s_data[31:0]!=frame_seq||s_data[63:32]!=~crc_state;
     end_crc<=s_data[63:32];end_seq<=s_data[31:0];
     if(fill!=0)begin state<=SEND;burst<=fill;index<=0;aw_sent<=0;data_sent<=0;end_pending<=1;fill<=0;end
     else begin
      invalid<=bad||!started||s_user==3||words!=EXPECTED_WORDS||s_data[31:0]!=frame_seq||s_data[63:32]!=~crc_state;
      frame_sequence<=s_data[31:0];crc<=s_data[63:32];commit<=1;started<=0;
     end
    end
   endcase
  end else begin
   if(m_axi_awvalid&&m_axi_awready)aw_sent<=1;
   if(m_axi_wvalid&&m_axi_wready)begin
    if(m_axi_wlast)data_sent<=1;else index<=index+1;
   end
   if(m_axi_bvalid&&m_axi_bready)begin
    if(m_axi_bresp!=0)bad<=1;
    address<=address+burst*8;state<=FILL;
    if(end_pending)begin
     invalid<=bad||m_axi_bresp!=0;frame_sequence<=end_seq;crc<=end_crc;commit<=1;started<=0;end_pending<=0;
    end
   end
  end
 end
endmodule
