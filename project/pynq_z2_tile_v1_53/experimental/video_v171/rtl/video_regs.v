// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// ARM configures enable once. All frame scheduling and decisions remain in PL.
module video_regs(
 (* X_INTERFACE_INFO="xilinx.com:signal:clock:1.0 clk CLK", X_INTERFACE_PARAMETER="XIL_INTERFACENAME clk, ASSOCIATED_BUSIF s_axi, ASSOCIATED_RESET resetn, FREQ_HZ 100000000" *) input wire clk,
 (* X_INTERFACE_INFO="xilinx.com:signal:reset:1.0 resetn RST", X_INTERFACE_PARAMETER="XIL_INTERFACENAME resetn, POLARITY ACTIVE_LOW" *) input wire resetn,
 input wire [7:0] s_axi_awaddr,input wire [2:0] s_axi_awprot,input wire s_axi_awvalid,output wire s_axi_awready,
 input wire [31:0] s_axi_wdata,input wire [3:0] s_axi_wstrb,input wire s_axi_wvalid,output wire s_axi_wready,
 output reg [1:0] s_axi_bresp=0,output reg s_axi_bvalid=0,input wire s_axi_bready,
 input wire [7:0] s_axi_araddr,input wire [2:0] s_axi_arprot,input wire s_axi_arvalid,output wire s_axi_arready,
 output reg [31:0] s_axi_rdata=0,output reg [1:0] s_axi_rresp=0,output reg s_axi_rvalid=0,input wire s_axi_rready,
 output reg enable=0,
 input wire [31:0] status,completed,rejected,capture_sequence,capture_crc,fault,peak,threshold,mask_pixels,core_sequence,core_cycles
);
 reg aw_pending=0,w_pending=0;reg [7:0] awaddr=0;
 reg [31:0] wdata=0;reg [3:0] wstrb=0;
 assign s_axi_awready=!aw_pending&&!s_axi_bvalid;
 assign s_axi_wready=!w_pending&&!s_axi_bvalid;
 assign s_axi_arready=!s_axi_rvalid;
 function automatic [31:0] reg_value(input [7:0] address);
  case(address)
   'h00:reg_value={31'b0,enable};'h04:reg_value=status;
   'h08:reg_value=completed;'h0c:reg_value=rejected;
   'h10:reg_value=capture_sequence;'h14:reg_value=capture_crc;
   'h18:reg_value=fault;'h1c:reg_value=peak;'h20:reg_value=threshold;
   'h24:reg_value=mask_pixels;'h28:reg_value=core_sequence;'h2c:reg_value=core_cycles;
   'h30:reg_value=32'h17100001;'h34:reg_value={16'd720,16'd720};
   default:reg_value=0;
  endcase
 endfunction
 always @(posedge clk)begin
  if(!resetn)begin
   enable<=0;aw_pending<=0;w_pending<=0;s_axi_bvalid<=0;s_axi_bresp<=0;
   s_axi_rvalid<=0;s_axi_rdata<=0;s_axi_rresp<=0;
  end else begin
   if(s_axi_awvalid&&s_axi_awready)begin awaddr<=s_axi_awaddr;aw_pending<=1;end
   if(s_axi_wvalid&&s_axi_wready)begin wdata<=s_axi_wdata;wstrb<=s_axi_wstrb;w_pending<=1;end
   if(aw_pending&&w_pending&&!s_axi_bvalid)begin
    if(awaddr==0&&wstrb[0])enable<=wdata[0];
    s_axi_bresp<=awaddr==0?0:2;s_axi_bvalid<=1;aw_pending<=0;w_pending<=0;
   end
   if(s_axi_bvalid&&s_axi_bready)s_axi_bvalid<=0;
   if(s_axi_arvalid&&s_axi_arready)begin
     s_axi_rdata<=reg_value(s_axi_araddr);s_axi_rresp<=(s_axi_araddr[1:0]==0&&s_axi_araddr<=8'h34) ? 0 : 2;s_axi_rvalid<=1;
   end
   if(s_axi_rvalid&&s_axi_rready)s_axi_rvalid<=0;
  end
 end
endmodule
