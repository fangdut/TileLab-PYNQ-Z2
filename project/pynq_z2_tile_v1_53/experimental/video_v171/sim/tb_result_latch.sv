`timescale 1ns/1ps
module tb_result_latch;
 reg clk=0;always #5 clk=~clk;
 reg resetn=0,request=0,arready=0,rvalid=0,rlast=0;
 reg [31:0] rdata=0;reg [1:0] rresp=0;
 wire busy,done,alarm,valid,arvalid,rready;
 wire [31:0] fault,seq,peak,threshold,pixels,araddr;
 wire [7:0] arlen;wire [2:0] arsize;wire [1:0] arburst;
 pl_result_latch #(.PIXELS(32)) dut(clk,resetn,request,busy,done,fault,seq,peak,threshold,pixels,alarm,valid,
 araddr,arlen,arsize,arburst,arvalid,arready,rdata,rresp,rlast,rvalid,rready);
 integer cycle=0;always @(posedge clk)begin cycle<=cycle+1;if(cycle>2000)$fatal(1,"Watchdog");end
 task send(input integer sequence_number,input integer corruption,input integer last_index);
  integer i;reg [31:0] h[0:9];begin
   h[0]=32'h17000001;h[1]=0;h[2]=1;h[3]=12000;h[4]=10908;
   h[5]=28;h[6]=5;h[7]=32;h[8]=47;h[9]=sequence_number;
   if(corruption==1)h[7]=33;
   @(negedge clk);request=1;@(negedge clk);request=0;
   wait(arvalid);
   repeat(7)begin
    @(negedge clk);if(!arvalid||araddr!=32'h07000000||arlen!=9||arsize!=2||arburst!=1)$fatal(1,"Read command unstable");
   end
   arready=1;@(negedge clk);arready=0;
   for(i=0;i<=last_index;i=i+1)begin
    repeat((i%3)+1)@(negedge clk);
    if(!rready)$fatal(1,"Unexpected read backpressure");
    rdata=i<10?h[i]:0;rresp=corruption==2&&i==5?2:0;rlast=i==last_index;rvalid=1;
    @(negedge clk);rvalid=0;
   end
   wait(done);@(negedge clk);
  end
 endtask
 task reset;
  begin resetn=0;repeat(3)@(negedge clk);resetn=1;end
 endtask
 initial begin
  reset();send(1,0,9);
  if(!valid||!alarm||fault||seq!=1||peak!=12000||threshold!=10908||pixels!=5)$fatal(1,"Header latch failed");
  send(2,0,9);if(!valid||seq!=2||fault)$fatal(1,"Consecutive frame failed");
  send(4,0,9);if(valid||fault!=8||seq!=2)$fatal(1,"Stale/skipped result accepted");
  reset();send(1,1,9);if(valid||fault!=8)$fatal(1,"Malformed header accepted");
  reset();send(1,2,9);if(valid||fault!=4)$fatal(1,"Read bus error accepted");
  reset();send(1,0,4);if(valid||fault!=4)$fatal(1,"Short read accepted");
  reset();send(1,0,12);if(valid||fault!=4)$fatal(1,"Long read accepted");
  $display("PL_RESULT_HEADER_SEQUENCE_BACKPRESSURE_ERRORS_PASS");$finish;
 end
endmodule
