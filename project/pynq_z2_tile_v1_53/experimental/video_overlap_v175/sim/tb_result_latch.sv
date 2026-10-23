`timescale 1ns/1ps
// Historical accepted RTL is the independent, unmodified semantic reference.
// Compare committed outputs, allowing the new two-cycle validation latency.
module tb_result_latch;
 reg clk=0;always #4 clk=~clk;
 reg resetn=0,request=0,m_axi_arready=0,m_axi_rvalid=0,m_axi_rlast=0;
 reg [31:0] m_axi_rdata=0;reg [1:0] m_axi_rresp=0;
 wire busy,done,m_axi_arvalid,m_axi_rready;
 wire [31:0] fault,frame_sequence,peak,threshold,mask_pixels,m_axi_araddr;
 wire alarm,valid;wire [7:0] m_axi_arlen;wire [2:0] m_axi_arsize;wire [1:0] m_axi_arburst;
 wire ref_busy,ref_done,ref_alarm,ref_valid,ref_arvalid,ref_rready;
 wire [31:0] ref_fault,ref_sequence,ref_peak,ref_threshold,ref_mask,ref_araddr;
 wire [7:0] ref_arlen;wire [2:0] ref_arsize;wire [1:0] ref_arburst;
 pl_result_latch dut(.*);
 pl_result_latch_reference_v176 golden(.clk(clk),.resetn(resetn),.request(request),
  .busy(ref_busy),.done(ref_done),.fault(ref_fault),.frame_sequence(ref_sequence),
  .peak(ref_peak),.threshold(ref_threshold),.mask_pixels(ref_mask),.alarm(ref_alarm),.valid(ref_valid),
  .m_axi_araddr(ref_araddr),.m_axi_arlen(ref_arlen),.m_axi_arsize(ref_arsize),.m_axi_arburst(ref_arburst),
  .m_axi_arvalid(ref_arvalid),.m_axi_arready(m_axi_arready),.m_axi_rdata(m_axi_rdata),
  .m_axi_rresp(m_axi_rresp),.m_axi_rlast(m_axi_rlast),.m_axi_rvalid(m_axi_rvalid),.m_axi_rready(ref_rready));
 reg [31:0] h[0:9];reg [31:0] rng=32'h18318ab5;
 integer count=0;
 function [31:0] random32();begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);random32=rng;end endfunction
 task compare_result;begin
  if({fault,frame_sequence,peak,threshold,mask_pixels,alarm,valid} !==
     {ref_fault,ref_sequence,ref_peak,ref_threshold,ref_mask,ref_alarm,ref_valid})
   $fatal(1,"Result mismatch at transaction %0d fault %h/%h seq %h/%h",count,fault,ref_fault,frame_sequence,ref_sequence);
 end endtask
 task reset_dut;begin
  @(negedge clk);resetn=0;request=0;m_axi_arready=0;m_axi_rvalid=0;m_axi_rlast=0;m_axi_rresp=0;
  repeat(3)@(negedge clk);resetn=1;@(negedge clk);compare_result();
 end endtask
 task header_good;begin
  h[0]=32'h17000001;h[1]=0;h[3]=random32();h[4]=random32();h[2]=h[3]>h[4];
  h[5]=28;h[6]=random32()%518401;h[7]=518400;h[8]=47;
  h[9]=valid?frame_sequence+32'd1:random32();
 end endtask
 task transaction(input integer beats,input integer bad_beat,input integer inject_busy);
 integer k,n;reg [193:0] old_result;begin
  if(busy||ref_busy)$fatal(1,"Overlapping test transaction");
  old_result={frame_sequence,peak,threshold,mask_pixels,alarm,valid};
  @(negedge clk);request=1;@(negedge clk);request=0;
  repeat(random32()%5)@(negedge clk);
  if(!m_axi_arvalid||!ref_arvalid||m_axi_araddr!=32'h07000000||m_axi_arlen!=9||m_axi_arsize!=2||m_axi_arburst!=1)
   $fatal(1,"Result AXI request changed");
  m_axi_arready=1;@(negedge clk);m_axi_arready=0;
  for(k=0;k<beats;k=k+1)begin
   repeat(random32()%4)@(negedge clk);
   if(!m_axi_rready||!ref_rready)$fatal(1,"Lost read readiness");
   m_axi_rdata=k<10?h[k]:random32();m_axi_rresp=k==bad_beat?2:0;
   m_axi_rlast=k==beats-1;m_axi_rvalid=1;request=inject_busy&&k==0;
   @(negedge clk);m_axi_rvalid=0;request=0;
  end
  m_axi_rlast=0;m_axi_rresp=0;
  // The extra validation stages must keep ownership busy and not publish early.
  for(n=0;n<3;n=n+1)begin
   if(!busy||done||{frame_sequence,peak,threshold,mask_pixels,alarm,valid}!==old_result)
    $fatal(1,"Premature result publication/ownership release");
   @(negedge clk);
  end
  if(!done||busy||ref_busy)$fatal(1,"Wrong commit latency");
  compare_result();count=count+1;
  @(negedge clk);if(done)$fatal(1,"Done wider than one cycle");
 end endtask
 integer i,j,mode;reg [31:0] ignored;
 initial begin
  reset_dut();header_good();h[9]=32'hffffffff;transaction(10,-1,0);
  header_good();h[9]=0;transaction(10,-1,0); // modulo32 sequence wrap
  for(i=0;i<2048;i=i+1)begin
   reset_dut();header_good();transaction(10,-1,0);
   header_good();mode=i%17;
   case(mode)
    0,1,2,3,4,5,6,7,8,9:h[mode]=h[mode]^32'hffffffff;
    10:begin h[3]=h[4];h[2]=0;end // equality: no alarm
    11:begin h[3]=32'hffffffff;h[4]=0;h[2]=1;end
    12:h[6]=518400; // inclusive maximum mask count
    13:h[6]=518401;
    14:h[2]=32'h80000001;
   endcase
   transaction(10,-1,0);
   header_good();transaction(10,-1,0); // sticky faults and recovery semantics
  end
  for(i=1;i<=32;i=i+1)begin
   reset_dut();header_good();transaction(i,-1,0);
  end
  for(i=0;i<10;i=i+1)begin reset_dut();header_good();transaction(10,i,0);end
  reset_dut();header_good();transaction(10,-1,1);
  // Reset while an incomplete DDR transaction owns the result latch.
  reset_dut();request=1;@(negedge clk);request=0;m_axi_arready=1;
  @(negedge clk);m_axi_arready=0;m_axi_rvalid=1;m_axi_rdata=32'h17000001;
  @(negedge clk);reset_dut();header_good();transaction(10,-1,0);
  $display("RESULT_LATCH_HISTORICAL_EQUIVALENCE_STALL_ERROR_SEQUENCE_WRAP_RESET_PASS transactions=%0d",count);
  $finish;
 end
 initial begin #20000000;$fatal(1,"Watchdog");end
endmodule
