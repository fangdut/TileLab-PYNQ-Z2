`timescale 1ns/1ps
// Integration fixture: HLS is a bus model here, not a CNN validation claim.
module tb_pipeline;
 reg control_clk=0,pixel_clk=0;always #7 control_clk=~control_clk;always #5 pixel_clk=~pixel_clk;
 reg control_resetn=0,pixel_resetn=0,enable=0;reg [23:0] hdmi_rgb=0;reg de=0,vs=0;
 wire [31:0] color_r=32'h100,color_g=32'h100,color_b=32'h100;
 wire color_changed=1'b0;wire color_config_ready;
 wire [31:0] status,completed,rejected,capture_sequence,capture_crc,fault,peak,threshold,mask_pixels,core_sequence,core_cycles,last_input_base,dropped;
 wire [31:0] m_axi_control_awaddr;
 wire [2:0] m_axi_control_awprot;
 wire  m_axi_control_awvalid;
 reg  m_axi_control_awready=0;
 wire [31:0] m_axi_control_wdata;
 wire [3:0] m_axi_control_wstrb;
 wire  m_axi_control_wvalid;
 reg  m_axi_control_wready=0;
 reg [1:0] m_axi_control_bresp=0;
 reg  m_axi_control_bvalid=0;
 wire  m_axi_control_bready;
 wire [31:0] m_axi_control_araddr;
 wire [2:0] m_axi_control_arprot;
 wire  m_axi_control_arvalid;
 reg  m_axi_control_arready=0;
 reg [31:0] m_axi_control_rdata=0;
 reg [1:0] m_axi_control_rresp=0;
 reg  m_axi_control_rvalid=0;
 wire  m_axi_control_rready;
 wire [31:0] m_axi_capture_awaddr;
 wire [7:0] m_axi_capture_awlen;
 wire [2:0] m_axi_capture_awsize;
 wire [1:0] m_axi_capture_awburst;
 wire  m_axi_capture_awvalid;
 reg  m_axi_capture_awready=0;
 wire [63:0] m_axi_capture_wdata;
 wire [7:0] m_axi_capture_wstrb;
 wire  m_axi_capture_wlast;
 wire  m_axi_capture_wvalid;
 reg  m_axi_capture_wready=0;
 reg [1:0] m_axi_capture_bresp=0;
 reg  m_axi_capture_bvalid=0;
 wire  m_axi_capture_bready;
 wire [31:0] m_axi_result_araddr;
 wire [7:0] m_axi_result_arlen;
 wire [2:0] m_axi_result_arsize;
 wire [1:0] m_axi_result_arburst;
 wire  m_axi_result_arvalid;
 reg  m_axi_result_arready=0;
 reg [31:0] m_axi_result_rdata=0;
 reg [1:0] m_axi_result_rresp=0;
 reg  m_axi_result_rlast=0;
 reg  m_axi_result_rvalid=0;
 wire  m_axi_result_rready;
 hdmi_detector_pipeline #(.FRAME_WIDTH(8),.FRAME_HEIGHT(4),.ROI_X(2),.ROI_Y(1),.ROI_WIDTH(4),.ROI_HEIGHT(2)) dut(.*);
 // Scale polling and simulated inference to the small video fixture. Require
 // actual DDR write handshakes during inference; no performance is inferred.
 defparam dut.scheduler.POLL_CYCLES=3;
 integer cycle=0,starts=0,running=0,wi=0,wrlen=0,rdindex=0;
 reg awgot=0,wgot=0,cawgot=0,cwgot=0,result_sending=0,hls_done=0;
 reg [31:0] wraddr=0,header[0:9];reg [63:0] buffer[0:15],image[0:15];
 reg [31:0] ctrl_addr=0,ctrl_data=0,input_pointer=0,infer_capture_seq=0,infer_capture_crc=0;
 reg [31:0] image_seq[0:3],image_crc[0:3];
 integer cap_slot=0,infer_slot=0,seen_completed=0,overlap_beats=0;
 function automatic [31:0] ref_crc(input integer which);
  reg [31:0] c;reg [7:0] b;
  begin
   c=32'hffffffff;
   for(integer w=0;w<4;w++)for(integer byte_i=0;byte_i<8;byte_i++)begin
    b=image[which*4+w]>>(byte_i*8);c=c^b;
    for(integer bit_i=0;bit_i<8;bit_i++)c=c[0]?(c>>1)^32'hedb88320:c>>1;
   end
   ref_crc=~c;
  end
 endfunction
 always @(negedge control_clk)if(control_resetn&&completed!=seen_completed)begin
  if(capture_sequence!=infer_capture_seq||capture_crc!=infer_capture_crc||last_input_base!=input_pointer)
   $fatal(1,"Published metadata is not paired with inferred input");
  seen_completed=completed;
 end
 integer i,j,yy,xx;reg [31:0] pixel;
 always @(posedge control_clk)begin
  cycle<=cycle+1;
  m_axi_capture_awready<=cycle%5==0;m_axi_capture_wready<=cycle%3==0;
  m_axi_control_awready<=cycle%7==0;m_axi_control_wready<=cycle%4==0;
  m_axi_control_arready<=!m_axi_control_rvalid;
  m_axi_result_arready<=cycle%9==0&&!result_sending&&!m_axi_result_rvalid;
  if(control_resetn)begin
   if(cycle>40000)$fatal(1,"Integration watchdog");
   if(fault)$fatal(1,"Unexpected pipeline fault %h",fault);
   if(m_axi_capture_awvalid&&m_axi_capture_awready)begin
    wraddr<=m_axi_capture_awaddr;wrlen<=m_axi_capture_awlen+1;awgot<=1;
   end
   if(m_axi_capture_wvalid&&m_axi_capture_wready)begin
    cap_slot=(m_axi_capture_awaddr-32'h06000000)>>22;
    if(cap_slot<0||cap_slot>3)$fatal(1,"Capture outside four slots");
    if((running>0||hls_done||result_sending)&&cap_slot==infer_slot)$fatal(1,"Capture overwrote inference input");
    if(completed&&m_axi_capture_awaddr==last_input_base)$fatal(1,"Capture overwrote result snapshot input");
    if(running>0)overlap_beats<=overlap_beats+1;
    buffer[wi]<=m_axi_capture_wdata;
    if(m_axi_capture_wlast)begin wgot<=1;wi<=0;end else wi<=wi+1;
   end
   if(awgot&&wgot&&!m_axi_capture_bvalid)begin
    cap_slot=(wraddr-32'h06000000)>>22;
    if(wrlen!=4||cap_slot<0||cap_slot>3||wraddr[21:0])$fatal(1,"Unexpected image burst %h %d",wraddr,wrlen);
    for(i=0;i<wrlen;i=i+1)image[cap_slot*4+i]<=buffer[i];
    m_axi_capture_bvalid<=1;awgot<=0;wgot<=0;
   end
   if(m_axi_capture_bvalid&&m_axi_capture_bready)m_axi_capture_bvalid<=0;
   if(dut.commit&&!dut.invalid)begin
    cap_slot=(dut.frame_base-32'h06000000)>>22;
    if(ref_crc(cap_slot)!=dut.captured_crc)$fatal(1,"Independent captured DDR CRC mismatch");
    image_seq[cap_slot]<=dut.captured_seq;image_crc[cap_slot]<=dut.captured_crc;
   end
   if(m_axi_control_awvalid&&m_axi_control_awready)begin
    if(m_axi_control_awaddr!=32'h43c10000&&m_axi_control_awaddr!=32'h43c10028)$fatal(1,"Wrong HLS control address");
    ctrl_addr<=m_axi_control_awaddr;cawgot<=1;
   end
   if(m_axi_control_wvalid&&m_axi_control_wready)begin
    ctrl_data<=m_axi_control_wdata;cwgot<=1;
   end
   if(cawgot&&cwgot&&!m_axi_control_bvalid)begin
    cawgot<=0;cwgot<=0;m_axi_control_bvalid<=1;
    if(ctrl_addr==32'h43c10028)begin
     if(running||result_sending)$fatal(1,"Pointer changed during inference");input_pointer<=ctrl_data;
    end else begin
    if(ctrl_data!=1||running||result_sending)$fatal(1,"Invalid or overlapping HLS start");
    infer_slot=(input_pointer-32'h06000000)>>22;
    if(infer_slot<0||infer_slot>3||input_pointer[21:0])$fatal(1,"Bad HLS pointer");
    infer_capture_seq<=image_seq[infer_slot];infer_capture_crc<=ref_crc(infer_slot);
    // The bus model checks every captured pixel, including Digilent's R,B,G.
    for(j=0;j<8;j=j+1)begin
     pixel=image[infer_slot*4+j/2]>>(32*(j%2));yy=1+j/4;xx=2+j%4;
     if(pixel[15:8]!=yy||pixel[7:0]!=xx||pixel[31:24]!=0)$fatal(1,"ROI/color packing mismatch %h",pixel);
    end
    starts<=starts+1;running<=387;hls_done<=0;end
   end
   if(m_axi_control_bvalid&&m_axi_control_bready)m_axi_control_bvalid<=0;
   if(running>0)begin
    running<=running-1;
    if(running==1)begin
     hls_done<=1;
     header[0]<=32'h17000001;header[1]<=0;header[2]<=starts%2;
     header[3]<=starts%2?12000:9000;header[4]<=10908;header[5]<=28;
     header[6]<=starts%2?3:0;header[7]<=8;header[8]<=47;header[9]<=starts;
    end
   end
   if(m_axi_control_arvalid&&m_axi_control_arready)begin
    m_axi_control_rvalid<=1;m_axi_control_rdata<=hls_done?2:0;hls_done<=0;
   end
   if(m_axi_control_rvalid&&m_axi_control_rready)m_axi_control_rvalid<=0;
   if(m_axi_result_arvalid&&m_axi_result_arready)begin
    if(m_axi_result_araddr!=32'h07000000||m_axi_result_arlen!=9)$fatal(1,"Wrong result header request");
    result_sending<=1;rdindex<=0;
   end
   if(result_sending&&!m_axi_result_rvalid&&cycle%3==0)begin
    m_axi_result_rdata<=header[rdindex];m_axi_result_rlast<=rdindex==9;m_axi_result_rvalid<=1;
   end
   if(m_axi_result_rvalid&&m_axi_result_rready)begin
    m_axi_result_rvalid<=0;
    if(m_axi_result_rlast)result_sending<=0;else rdindex<=rdindex+1;
   end
  end
 end
 task frame(input integer rows,input integer id);
  integer x,y;begin
   @(negedge pixel_clk);vs=1;de=0;
   repeat(12)@(negedge pixel_clk);vs=0;
   for(y=0;y<rows;y=y+1)begin
    for(x=0;x<8;x=x+1)begin de=1;hdmi_rgb={8'(id),8'(x),8'(y)};@(negedge pixel_clk);end
    de=0;repeat(4)@(negedge pixel_clk);
   end
   repeat(10)@(negedge pixel_clk);
  end
 endtask
 integer f=1;
 initial begin
  repeat(10)@(negedge control_clk);control_resetn=1;pixel_resetn=1;
  repeat(100)@(negedge pixel_clk);enable=1;
  repeat(80)@(negedge pixel_clk);
  forever begin frame(f==1?3:4,f);f=f+1;end
 end
 initial begin
  wait(completed==3);@(negedge control_clk);enable=0;wait(!status[0]);
  $display("OVERLAP_DIAGNOSTIC starts=%0d core_seq=%0d peak=%0d status=%h rejected=%0d core_cycles=%0d overlap_beats=%0d dropped=%0d",starts,core_sequence,peak,status,rejected,core_cycles,overlap_beats,dropped);
  if(starts!=3||core_sequence!=3||peak!=12000||!status[2]||!status[3]||rejected<1||!core_cycles||overlap_beats==0||dropped==0)$fatal(1,"Continuous result/ownership failure");
  $display("PL_OVERLAP_ROI_DYNAMIC_DDR_POINTER_RESULT_CORRELATION_PASS");$finish;
 end
endmodule
