`timescale 1ns/1ps
module tb_scheduler;
 reg clk=0;always #5 clk=~clk;
 reg resetn=0,enable=0,commit=0,invalid=0;reg [31:0] seq=0,crc=0;
 wire request,owner,publish,capture_active;wire [31:0] completed,rejected,last_seq,last_crc,fault;
 wire [31:0] awaddr,wdata,araddr;wire [2:0] awprot,arprot;wire [3:0] strb;
 wire awvalid,wvalid,bready,arvalid,rready;
 reg awready=0,wready=0,bvalid=0,arready=0,rvalid=0;reg [1:0] bresp=0,rresp=0;reg [31:0] rdata=0;
 pl_frame_scheduler #(.POLL_CYCLES(3)) dut(clk,resetn,enable,commit,invalid,seq,crc,request,owner,publish,
 completed,rejected,last_seq,last_crc,fault,awaddr,awprot,awvalid,awready,wdata,strb,wvalid,wready,bresp,bvalid,bready,
 araddr,arprot,arvalid,arready,rdata,rresp,rvalid,rready,capture_active);
 integer cycle=0,writes=0,remaining=0,publishes=0;reg got_aw=0,got_w=0,inject_error=0;
 reg hold_aw=0,hold_w=0,hold_ar=0;
 always @(posedge clk)begin
  cycle<=cycle+1;
  // Independent, non-identical stalls on AW, W and AR.
  awready<=cycle%5==0;wready<=cycle%7==0;arready<=cycle%3==0;
  if(resetn)begin
   if(hold_aw&&!awvalid)$fatal(1,"AWVALID dropped under backpressure");
   if(hold_w&&!wvalid)$fatal(1,"WVALID dropped under backpressure");
   if(hold_ar&&!arvalid)$fatal(1,"ARVALID dropped under backpressure");
   if(awvalid&&(awaddr!=32'h43c10000||awprot))$fatal(1,"Wrong start address");
   if(wvalid&&(wdata!=1||strb!=15))$fatal(1,"Wrong HLS command");
   if(awvalid&&awready)got_aw<=1;
   if(wvalid&&wready)got_w<=1;
   if(got_aw&&got_w&&!bvalid)begin
    bvalid<=1;bresp<=inject_error?2:0;got_aw<=0;got_w<=0;writes<=writes+1;remaining<=37;
   end
   if(bvalid&&bready)bvalid<=0;
   if(remaining>0)remaining<=remaining-1;
   if(arvalid&&arready)begin rvalid<=1;rdata<=remaining==0?2:0;rresp<=0;end
   if(rvalid&&rready)rvalid<=0;
   if(publish)publishes<=publishes+1;
  end
  hold_aw<=awvalid&&!awready;hold_w<=wvalid&&!wready;hold_ar<=arvalid&&!arready;
  if(cycle>5000)$fatal(1,"Watchdog");
 end
 task frame(input bit bad,input integer index);
  reg old;begin
   old=request;wait(request!=old);
   repeat(11)@(negedge clk);seq=index;crc=32'hb0010000+index;invalid=bad;commit=1;
   @(negedge clk);commit=0;invalid=0;
  end
 endtask
 initial begin
  repeat(4)@(negedge clk);resetn=1;enable=1;
  frame(0,1);wait(completed==1);
  if(last_seq!=1||last_crc!=32'hb0010001)$fatal(1,"Frame identity mismatch");
  frame(1,2);wait(rejected==1);
  if(writes!=1)$fatal(1,"Invalid frame launched inference");
  frame(0,3);wait(completed==2);
  if(last_seq!=3||writes!=2)$fatal(1,"Continuous hardware handoff failed");
  inject_error=1;frame(0,4);wait(fault==1);
  repeat(20)@(negedge clk);if(writes!=3||completed!=2)$fatal(1,"Bus fault did not stop inference");
  enable=0;repeat(3)@(negedge clk);if(owner)$fatal(1,"Ownership not released");
  $display("PL_SCHEDULER_BACKPRESSURE_INVALID_FRAME_BUS_FAULT_PASS");$finish;
 end
endmodule
