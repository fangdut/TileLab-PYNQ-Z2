`timescale 1ns/1ps
module tb_writer;
 reg clk=0;always #5 clk=~clk;
 reg [31:0] frame_base=32'h06000f80,expected_base=32'h06000f80;reg resetn=0;reg [63:0] data=0;reg [1:0] user=0;reg valid=0;wire ready,commit,invalid;wire [31:0] frame_seq,crc;
 wire [31:0] awaddr;wire [7:0] awlen,wstrb;wire [2:0] awsize;wire [1:0] awburst;wire awvalid,wlast,wvalid,bready;wire [63:0] wdata;
 reg awready=0,wready=0,bvalid=0;reg [1:0] bresp=0;
 roi_ddr_writer #(.BASE(32'h06000f80),.EXPECTED_WORDS(20)) dut(clk,resetn,data,user,valid,ready,commit,invalid,frame_seq,crc,awaddr,awlen,awsize,awburst,awvalid,awready,wdata,wstrb,wlast,wvalid,wready,bresp,bvalid,bready,frame_base);
 function automatic [63:0] pattern(input integer seq,input integer index);pattern=64'hf1e2d3c4b5a69788^(seq<<16)^index;endfunction
 function automatic [31:0] golden_crc(input integer seq);case(seq)
7:golden_crc=32'h5da79e07;
8:golden_crc=32'h8de787f1;
9:golden_crc=32'h97ce28fa;
10:golden_crc=32'haddffd6d;
 11:golden_crc=32'hdae82b2a;
 default:golden_crc=0;endcase endfunction
 integer cycle=0,beats=0,expect_index=0,current_seq=0,length=0,bursts=0,published=0,last_position=-1;reg got_aw=0,hold_w=0,hold_aw=0;reg [63:0] held_data;reg held_last;
 always @(posedge clk)begin
  cycle<=cycle+1;awready<=cycle%7==0;wready<=cycle%3==0;
  if(resetn)begin
   if(hold_aw&&!awvalid)$fatal(1,"AW dropped while stalled");
   if(hold_w&&(!wvalid||wdata!=held_data||wlast!=held_last))$fatal(1,"Write data changed while stalled");
   if(awvalid&&awready)begin
    if(awsize!=3||awburst!=1||awaddr!=expected_base+expect_index*8||awaddr[11:0]+(int'(awlen)+1)*8>4096)$fatal(1,"Burst address/4K violation");
    got_aw<=1;length<=awlen+1;bursts<=bursts+1;
   end
   if(wvalid&&wready)begin
    if(wstrb!=255||wdata!=pattern(current_seq,expect_index+beats))$fatal(1,"Memory data mismatch");
    if(wlast)begin if(last_position>=0)$fatal(1,"Multiple WLAST");last_position<=beats;end
    beats<=beats+1;
   end
   if(got_aw&&beats==length&&!bvalid)begin if(last_position!=length-1)$fatal(1,"WLAST position mismatch");bvalid<=1;got_aw<=0;expect_index<=expect_index+beats;beats<=0;end
   if(bvalid&&bready)begin bvalid<=0;last_position<=-1;end
   if(commit)begin if(bvalid||got_aw||beats)$fatal(1,"Published before write response");published<=published+1;end
  end
  hold_aw<=awvalid&&!awready;hold_w<=wvalid&&!wready;held_data<=wdata;held_last<=wlast;
  if(cycle>8000)$fatal(1,"Writer watchdog");
 end
 task push(input [63:0] d,input [1:0] u);begin
  @(negedge clk);data=d;user=u;valid=1;
  do @(posedge clk);while(!ready);
  @(negedge clk);valid=0;
 end endtask
 task frame(input integer seq,input integer n,input bit corrupt,input bit bad);integer i;begin
  current_seq=seq;expect_index=0;expected_base=32'h06000f80+((seq%4)<<22);frame_base=expected_base;bresp=seq==11?2:0;push(seq,1);frame_base=32'h0;
  for(i=0;i<n;i=i+1)push(pattern(seq,i),0);
  push({(golden_crc(seq)^(corrupt?32'h1:32'h0)),32'(seq)},2);
  wait(commit);if(invalid!=bad||frame_seq!=seq)$fatal(1,"Invalid frame accepted or identity lost");
  repeat(4)@(negedge clk);
 end endtask
 initial begin
  repeat(4)@(negedge clk);resetn=1;
  frame(7,20,0,0);frame(8,20,1,1);frame(9,3,0,1);frame(10,21,0,1);frame(11,20,0,1);
  if(published!=5)$fatal(1,"Missing completion");
  $display("PL_DYNAMIC_SLOT_WRITER_CRC_LENGTH_BACKPRESSURE_COMMIT_PASS");$finish;
 end
endmodule
