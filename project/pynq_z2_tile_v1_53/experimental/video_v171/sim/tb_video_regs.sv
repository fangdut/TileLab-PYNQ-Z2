`timescale 1ns/1ps
module tb_video_regs;
 reg clk=0;always #5 clk=~clk;
 reg resetn=0;reg [7:0] awaddr=0,araddr=0;
 reg awvalid=0,wvalid=0,bready=0,arvalid=0,rready=0;
 reg [31:0] wdata=0;reg [3:0] wstrb=0;
 wire awready,wready,bvalid,arready,rvalid,enable;wire [1:0] bresp,rresp;wire [31:0] rdata;
 reg [31:0] status=32'h1234,completed=77;
 video_regs dut(.clk(clk),.resetn(resetn),.s_axi_awaddr(awaddr),.s_axi_awprot(3'b0),.s_axi_awvalid(awvalid),.s_axi_awready(awready),
 .s_axi_wdata(wdata),.s_axi_wstrb(wstrb),.s_axi_wvalid(wvalid),.s_axi_wready(wready),.s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(bready),
 .s_axi_araddr(araddr),.s_axi_arprot(3'b0),.s_axi_arvalid(arvalid),.s_axi_arready(arready),.s_axi_rdata(rdata),.s_axi_rresp(rresp),.s_axi_rvalid(rvalid),.s_axi_rready(rready),
 .enable(enable),.status(status),.completed(completed),.rejected(32'd2),.capture_sequence(32'd90),.capture_crc(32'hdeadbeef),.fault(32'd0),
 .peak(32'd12000),.threshold(32'd10908),.mask_pixels(32'd3),.core_sequence(32'd77),.core_cycles(32'd1000000));
 integer cycles=0;always @(posedge clk)begin cycles<=cycles+1;if(cycles>2000)$fatal(1,"Watchdog");end
 task address(input [7:0] a);
  begin @(negedge clk);awaddr=a;awvalid=1;do @(posedge clk);while(!awready);@(negedge clk);awvalid=0;awaddr=8'hfc;end
 endtask
 task data(input [31:0] d,input [3:0] s);
  begin @(negedge clk);wdata=d;wstrb=s;wvalid=1;do @(posedge clk);while(!wready);@(negedge clk);wvalid=0;wdata=~d;end
 endtask
 task response(input [1:0] expected);
  begin
   wait(bvalid);repeat(9)begin @(negedge clk);if(!bvalid||bresp!=expected||awready||wready)$fatal(1,"Write response/backpressure failed");end
   bready=1;@(negedge clk);bready=0;
  end
 endtask
 task read(input [7:0] a,input [31:0] value,input [1:0] resp);
  begin
   @(negedge clk);araddr=a;arvalid=1;do @(posedge clk);while(!arready);@(negedge clk);arvalid=0;araddr=8'hfc;
   wait(rvalid);repeat(5)begin @(negedge clk);if(!rvalid||rdata!==value||rresp!=resp||arready)$fatal(1,"Read stability/address failed %h %h",a,rdata);end
   rready=1;@(negedge clk);rready=0;
  end
 endtask
 initial begin
  repeat(4)@(negedge clk);resetn=1;
  address(0);repeat(7)@(negedge clk);if(enable)$fatal(1,"Incomplete write changed enable");data(1,1);response(0);if(!enable)$fatal(1,"Enable write failed");
  data(0,1);repeat(7)@(negedge clk);if(!enable)$fatal(1,"Data-only write changed enable");address(0);response(0);if(enable)$fatal(1,"Data-before-address latch failed");
  address(0);data(1,8);response(0);if(enable)$fatal(1,"Byte strobe ignored");
  address(4);data(1,15);response(2);if(enable)$fatal(1,"Read-only write changed enable");
  read(0,0,0);read(4,32'h1234,0);read(8,77,0);read(12,2,0);read(16,90,0);read(20,32'hdeadbeef,0);
  read(24,0,0);read(28,12000,0);read(32,10908,0);read(36,3,0);read(40,77,0);read(44,1000000,0);
  read(48,32'h17100001,0);read(52,{16'd720,16'd720},0);read(5,0,2);read(60,0,2);
  $display("VIDEO_REGS_INDEPENDENT_AW_W_STROBES_READONLY_BACKPRESSURE_PASS");$finish;
 end
endmodule
