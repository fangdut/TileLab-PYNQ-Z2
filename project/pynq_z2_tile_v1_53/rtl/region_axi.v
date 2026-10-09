// Read-only, single outstanding AXI-Lite peripheral. Writes return SLVERR.
// 0x00 frame sequence, 0x04 status (count[3:0], overflow[8], invalid[31]),
// 0x08..0x47 eight {ymin,xmin}/{ymax,xmax}, 0x48..0x67 eight areas.
module region_axi(
 (* X_INTERFACE_PARAMETER="XIL_INTERFACENAME s_axi_aclk, ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET s_axi_aresetn" *)
 input wire s_axi_aclk,input wire s_axi_aresetn,
 input wire [831:0] snapshot,
 input wire [11:0] s_axi_awaddr,input wire [2:0] s_axi_awprot,input wire s_axi_awvalid,output wire s_axi_awready,
 input wire [31:0] s_axi_wdata,input wire [3:0] s_axi_wstrb,input wire s_axi_wvalid,output wire s_axi_wready,
 output wire [1:0] s_axi_bresp,output reg s_axi_bvalid=0,input wire s_axi_bready,
 input wire [11:0] s_axi_araddr,input wire [2:0] s_axi_arprot,input wire s_axi_arvalid,output wire s_axi_arready,
 output reg [31:0] s_axi_rdata=0,output wire [1:0] s_axi_rresp,output reg s_axi_rvalid=0,input wire s_axi_rready);
 reg aw=0,wd=0;
 assign s_axi_awready=!aw && !s_axi_bvalid;assign s_axi_wready=!wd && !s_axi_bvalid;
 assign s_axi_bresp=2'b10;assign s_axi_rresp=0;assign s_axi_arready=!s_axi_rvalid;
 always @(posedge s_axi_aclk)begin
  if(!s_axi_aresetn)begin aw<=0;wd<=0;s_axi_bvalid<=0;s_axi_rvalid<=0;s_axi_rdata<=0;end
  else begin
   if(s_axi_awvalid && s_axi_awready)aw<=1;
   if(s_axi_wvalid && s_axi_wready)wd<=1;
   if(aw && wd && !s_axi_bvalid)begin s_axi_bvalid<=1;aw<=0;wd<=0;end
   if(s_axi_bvalid && s_axi_bready)s_axi_bvalid<=0;
   if(s_axi_rvalid && s_axi_rready)s_axi_rvalid<=0;
   if(s_axi_arvalid && s_axi_arready)begin
    s_axi_rvalid<=1;s_axi_rdata<=0;
    if(s_axi_araddr[11:2]<26)s_axi_rdata<=snapshot[s_axi_araddr[11:2]*32+:32];
   end
  end
 end
endmodule
