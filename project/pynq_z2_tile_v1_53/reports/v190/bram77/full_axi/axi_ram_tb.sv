// SPDX-License-Identifier: MIT
// Bounded AXI4 simulation memory. One outstanding burst per direction.
`timescale 1ns/1ps
module axi_ram_tb #(parameter D=32, WORDS=8192)(
 input wire clk,rst_n,
 input wire AWVALID,output wire AWREADY,input wire[63:0] AWADDR,input wire AWID,input wire[7:0] AWLEN,input wire[2:0] AWSIZE,input wire[1:0] AWBURST,
 input wire WVALID,output wire WREADY,input wire[D-1:0] WDATA,input wire[D/8-1:0] WSTRB,input wire WLAST,
 output reg BVALID=0,input wire BREADY,output reg BID=0,output wire[1:0] BRESP,
 input wire ARVALID,output wire ARREADY,input wire[63:0] ARADDR,input wire ARID,input wire[7:0] ARLEN,input wire[2:0] ARSIZE,input wire[1:0] ARBURST,
 output reg RVALID=0,input wire RREADY,output reg[D-1:0] RDATA=0,output reg RLAST=0,output reg RID=0,output wire[1:0] RRESP
);
 localparam B=D/8, SHIFT=$clog2(B);
 reg[D-1:0] mem[0:WORDS-1];
 reg reading=0,writing=0;reg[63:0] ra=0,wa=0;integer rn=0,wn=0,rl=0,wl=0,cycle=0;
 integer writes=0,reads=0,stalls=0;
 assign AWREADY=rst_n&&!writing&&!BVALID;
 assign WREADY=rst_n&&writing&&(cycle%7!=0);
 assign ARREADY=rst_n&&!reading&&!RVALID;
 assign BRESP=0;assign RRESP=0;
 integer byte_lane;
 always @(posedge clk) begin
  if(!rst_n)begin reading<=0;writing<=0;RVALID<=0;BVALID<=0;cycle<=0;end
  else begin
   cycle<=cycle+1;
   if((RVALID&&!RREADY)||(WVALID&&!WREADY))stalls<=stalls+1;
   if(ARVALID&&ARREADY)begin
    if(ARSIZE!=SHIFT||ARBURST!=1||ARADDR%B!=0||(ARADDR>>SHIFT)+ARLEN>=WORDS)$fatal(1,"AXI_READ_RANGE_OR_FORMAT");
    reading<=1;ra<=ARADDR;rn<=0;rl<=ARLEN;RID<=ARID;
   end
   if(reading&&!RVALID&&(cycle%5!=0))begin RDATA<=mem[(ra>>SHIFT)+rn];RLAST<=rn==rl;RVALID<=1;end
   if(RVALID&&RREADY)begin RVALID<=0;reads<=reads+1;if(RLAST)reading<=0;else rn<=rn+1;end
   if(AWVALID&&AWREADY)begin
    if(AWSIZE!=SHIFT||AWBURST!=1||AWADDR%B!=0||(AWADDR>>SHIFT)+AWLEN>=WORDS)$fatal(1,"AXI_WRITE_RANGE_OR_FORMAT");
    writing<=1;wa<=AWADDR;wn<=0;wl<=AWLEN;BID<=AWID;
   end
   if(WVALID&&WREADY)begin
    if(WLAST!=(wn==wl))$fatal(1,"AXI_WLAST_MISMATCH");
    for(byte_lane=0;byte_lane<B;byte_lane=byte_lane+1)if(WSTRB[byte_lane])mem[(wa>>SHIFT)+wn][byte_lane*8+:8]<=WDATA[byte_lane*8+:8];
    writes<=writes+1;
    if(WLAST)begin writing<=0;BVALID<=1;end else wn<=wn+1;
   end
   if(BVALID&&BREADY)BVALID<=0;
  end
 end
endmodule
