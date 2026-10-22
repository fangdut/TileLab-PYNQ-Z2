// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Isolated prototype. Not connected to the accepted video pipeline.
// Pull/grant interface: a requester reserves its slot on grant, then uses it
// until commit/done. Capture commit follows the LAST DDR B response. Infer
// done follows the complete result latch, including all mask/header reads.
// A replaceable latest-ready slot is never offered as an AXI VALID payload.
module frame_slot_queue #(
 parameter logic [31:0] BASE=32'h06000000,
 parameter logic [31:0] STRIDE=32'h00400000
)(
 input wire clk,resetn,enable,
 input wire capture_acquire,capture_commit,capture_invalid,
 input wire [31:0] capture_sequence,capture_crc,
 output logic capture_grant=0,
 output logic [31:0] capture_base=BASE,
 output wire capture_busy,
 input wire infer_acquire,infer_done,
 output logic infer_grant=0,
 output logic [31:0] infer_base=BASE,infer_sequence=0,infer_crc=0,
 output wire infer_busy,ready_available,
 output logic result_commit=0,
 output logic [31:0] last_base=BASE,last_sequence=0,last_crc=0,
 output wire last_valid,drained,
 output logic [31:0] completed=0,rejected=0,dropped=0,fault=0
);
 logic cvalid=0,rvalid=0,ivalid=0,lvalid=0;
 logic [1:0] cslot=0,rslot=0,islot=0,lslot=0;
 logic [31:0] rsequence=0,rcrc=0;
 logic nc,nr,ni,nl;
 logic [1:0] cs,rs,is,ls;
 logic [31:0] rseqn,rcrcn;
 logic [3:0] used;
 integer free_slot;
 assign capture_busy=cvalid;
 assign infer_busy=ivalid;
 assign ready_available=rvalid;
 assign last_valid=lvalid;
 assign drained=!cvalid&&!ivalid&&!rvalid;
 function automatic [31:0] address(input [1:0] slot);
  address=BASE+slot*STRIDE;
 endfunction
 always @(posedge clk)begin
  capture_grant<=0;infer_grant<=0;result_commit<=0;
  if(!resetn)begin
   cvalid<=0;rvalid<=0;ivalid<=0;lvalid<=0;
   cslot<=0;rslot<=0;islot<=0;lslot<=0;rsequence<=0;rcrc<=0;
   capture_base<=BASE;infer_base<=BASE;infer_sequence<=0;infer_crc<=0;
   last_base<=BASE;last_sequence<=0;last_crc<=0;
   completed<=0;rejected<=0;dropped<=0;fault<=0;
  end else begin
   fault<=fault|(capture_commit&&!cvalid?32'h1:32'h0)|(infer_done&&!ivalid?32'h2:32'h0);
   nc=cvalid;nr=rvalid;ni=ivalid;nl=lvalid;
   cs=cslot;rs=rslot;is=islot;ls=lslot;rseqn=rsequence;rcrcn=rcrc;
   // Preserve the completed inference input for host snapshot correlation.
   if(infer_done)begin
    if(ivalid)begin
     ni=0;nl=1;ls=islot;
     last_base<=infer_base;last_sequence<=infer_sequence;last_crc<=infer_crc;
     completed<=completed+1;result_commit<=1;
    end
   end
   // Pop the old ready frame before processing a simultaneous capture commit.
   if(enable&&infer_acquire&&!ni&&nr)begin
    ni=1;is=rs;nr=0;
    infer_base<=address(rs);infer_sequence<=rseqn;infer_crc<=rcrcn;infer_grant<=1;
   end
   if(capture_commit)begin
    if(cvalid)begin
     nc=0;
     if(capture_invalid)rejected<=rejected+1;
     else if(enable)begin
      if(nr)dropped<=dropped+1;
      nr=1;rs=cslot;rseqn=capture_sequence;rcrcn=capture_crc;
     end
    end
   end
   // Disable drains outstanding owners; unconsumed ready data is discarded.
   if(!enable)nr=0;
   used=0;
   if(nc)used[cs]=1;if(nr)used[rs]=1;if(ni)used[is]=1;if(nl)used[ls]=1;
   free_slot=-1;
   for(integer n=3;n>=0;n=n-1)if(!used[n])free_slot=n;
   if(enable&&capture_acquire&&!nc&&free_slot>=0)begin
    nc=1;cs=free_slot;capture_base<=address(cs);capture_grant<=1;
   end
   cvalid<=nc;rvalid<=nr;ivalid<=ni;lvalid<=nl;
   cslot<=cs;rslot<=rs;islot<=is;lslot<=ls;rsequence<=rseqn;rcrc<=rcrcn;
  end
 end
endmodule
