// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Capture -> DDR -> HLS -> header verification -> next capture: no CPU frame loop.
module hdmi_detector_pipeline #(
 parameter integer FRAME_WIDTH=1280,FRAME_HEIGHT=720,ROI_X=280,ROI_Y=0,ROI_WIDTH=720,ROI_HEIGHT=720
)(
 (* X_INTERFACE_INFO="xilinx.com:signal:clock:1.0 control_clk CLK", X_INTERFACE_PARAMETER="XIL_INTERFACENAME control_clk, ASSOCIATED_BUSIF m_axi_control:m_axi_capture:m_axi_result, ASSOCIATED_RESET control_resetn" *) input wire control_clk,
 (* X_INTERFACE_INFO="xilinx.com:signal:reset:1.0 control_resetn RST", X_INTERFACE_PARAMETER="XIL_INTERFACENAME control_resetn, POLARITY ACTIVE_LOW" *) input wire control_resetn,
 input wire pixel_clk,pixel_resetn,enable,
 input wire [31:0] color_r,color_g,color_b,input wire color_changed,
 output wire color_config_ready,
 // Digilent dvi2rgb encodes channels as R,B,G. Reorder exactly once here.
 input wire [23:0] hdmi_rgb,input wire de,vs,
 output wire [31:0] status,completed,rejected,capture_sequence,capture_crc,fault,peak,threshold,mask_pixels,core_sequence,last_input_base,dropped,
 output reg [31:0] core_cycles=0,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control AWADDR" *) output wire [31:0] m_axi_control_awaddr,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control AWPROT" *) output wire [2:0] m_axi_control_awprot,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control AWVALID" *) output wire  m_axi_control_awvalid,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control AWREADY" *) input wire  m_axi_control_awready,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control WDATA" *) output wire [31:0] m_axi_control_wdata,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control WSTRB" *) output wire [3:0] m_axi_control_wstrb,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control WVALID" *) output wire  m_axi_control_wvalid,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control WREADY" *) input wire  m_axi_control_wready,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control BRESP" *) input wire [1:0] m_axi_control_bresp,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control BVALID" *) input wire  m_axi_control_bvalid,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control BREADY" *) output wire  m_axi_control_bready,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control ARADDR" *) output wire [31:0] m_axi_control_araddr,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control ARPROT" *) output wire [2:0] m_axi_control_arprot,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control ARVALID" *) output wire  m_axi_control_arvalid,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control ARREADY" *) input wire  m_axi_control_arready,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control RDATA" *) input wire [31:0] m_axi_control_rdata,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control RRESP" *) input wire [1:0] m_axi_control_rresp,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control RVALID" *) input wire  m_axi_control_rvalid,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_control RREADY" *) output wire  m_axi_control_rready,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture AWADDR" *) output wire [31:0] m_axi_capture_awaddr,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture AWLEN" *) output wire [7:0] m_axi_capture_awlen,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture AWSIZE" *) output wire [2:0] m_axi_capture_awsize,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture AWBURST" *) output wire [1:0] m_axi_capture_awburst,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture AWVALID" *) output wire  m_axi_capture_awvalid,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture AWREADY" *) input wire  m_axi_capture_awready,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture WDATA" *) output wire [63:0] m_axi_capture_wdata,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture WSTRB" *) output wire [7:0] m_axi_capture_wstrb,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture WLAST" *) output wire  m_axi_capture_wlast,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture WVALID" *) output wire  m_axi_capture_wvalid,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture WREADY" *) input wire  m_axi_capture_wready,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture BRESP" *) input wire [1:0] m_axi_capture_bresp,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture BVALID" *) input wire  m_axi_capture_bvalid,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_capture BREADY" *) output wire  m_axi_capture_bready,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_result ARADDR" *) output wire [31:0] m_axi_result_araddr,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_result ARLEN" *) output wire [7:0] m_axi_result_arlen,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_result ARSIZE" *) output wire [2:0] m_axi_result_arsize,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_result ARBURST" *) output wire [1:0] m_axi_result_arburst,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_result ARVALID" *) output wire  m_axi_result_arvalid,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_result ARREADY" *) input wire  m_axi_result_arready,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_result RDATA" *) input wire [31:0] m_axi_result_rdata,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_result RRESP" *) input wire [1:0] m_axi_result_rresp,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_result RLAST" *) input wire  m_axi_result_rlast,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_result RVALID" *) input wire  m_axi_result_rvalid,
 (* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 m_axi_result RREADY" *) output wire  m_axi_result_rready
);
 wire [63:0] data;wire [1:0] user;wire valid,ready,commit,invalid,active,owner,publish;
 wire [31:0] captured_seq,captured_crc,schedule_fault,result_fault;
 wire result_done,result_busy,result_alarm,result_valid,infer_start;
 wire [31:0] frame_base;
 wire [23:0] calibrated_rgb;wire calibrated_de,calibrated_vs,color_pixel_resetn;
 video_color_correct color(
  .control_clk(control_clk),.control_resetn(control_resetn),.pixel_clk(pixel_clk),.pixel_resetn(color_pixel_resetn),
  .config_r(color_r),.config_g(color_g),.config_b(color_b),.config_changed(color_changed),.config_ready(color_config_ready),
  .rgb({hdmi_rgb[23:16],hdmi_rgb[7:0],hdmi_rgb[15:8]}),.de(de),.vs(vs),
  .rgb_out(calibrated_rgb),.de_out(calibrated_de),.vs_out(calibrated_vs));
 (* ASYNC_REG="TRUE" *) reg [2:0] lock_sync=0;
 reg [31:0] ticks=0,started=0;
 always @(posedge control_clk)begin
  if(!control_resetn)begin lock_sync<=0;ticks<=0;started<=0;core_cycles<=0;end
  else begin
   lock_sync<={lock_sync[1:0],pixel_resetn};ticks<=ticks+1;
   if(infer_start)started<=ticks;
   if(result_done)core_cycles<=ticks-started;
  end
 end
 assign status={26'b0,lock_sync[2],(|fault),result_valid,result_alarm,active,owner};
 assign fault=schedule_fault|(result_fault<<8);
 video_capture_link #(.FRAME_WIDTH(FRAME_WIDTH),.FRAME_HEIGHT(FRAME_HEIGHT),.ROI_X(ROI_X),.ROI_Y(ROI_Y),.ROI_WIDTH(ROI_WIDTH),.ROI_HEIGHT(ROI_HEIGHT)) capture(
  .pixel_clk(pixel_clk),.pixel_resetn(pixel_resetn),.control_clk(control_clk),.control_resetn(control_resetn),.capture_active(active),
  .rgb(calibrated_rgb),.de(calibrated_de),.vs(calibrated_vs),.data(data),.user(user),.valid(valid),.ready(ready),.producer_resetn(color_pixel_resetn));
 roi_ddr_writer #(.EXPECTED_WORDS(ROI_WIDTH*ROI_HEIGHT/2)) writer(
  .clk(control_clk),.resetn(control_resetn),.s_data(data),.s_user(user),.s_valid(valid),.s_ready(ready),
  .commit(commit),.invalid(invalid),.frame_sequence(captured_seq),.crc(captured_crc),.frame_base(frame_base),
  .m_axi_awaddr(m_axi_capture_awaddr),
  .m_axi_awlen(m_axi_capture_awlen),
  .m_axi_awsize(m_axi_capture_awsize),
  .m_axi_awburst(m_axi_capture_awburst),
  .m_axi_awvalid(m_axi_capture_awvalid),
  .m_axi_awready(m_axi_capture_awready),
  .m_axi_wdata(m_axi_capture_wdata),
  .m_axi_wstrb(m_axi_capture_wstrb),
  .m_axi_wlast(m_axi_capture_wlast),
  .m_axi_wvalid(m_axi_capture_wvalid),
  .m_axi_wready(m_axi_capture_wready),
  .m_axi_bresp(m_axi_capture_bresp),
  .m_axi_bvalid(m_axi_capture_bvalid),
  .m_axi_bready(m_axi_capture_bready));
 pl_frame_scheduler_overlap scheduler(
  .clk(control_clk),.resetn(control_resetn),.enable(enable&&color_config_ready),.capture_commit(commit),.capture_invalid(invalid),
  .capture_sequence(captured_seq),.capture_crc(captured_crc),.owner(owner),.result_publish(publish),
  .capture_base(frame_base),.last_input_base(last_input_base),.dropped(dropped),.start_pulse(infer_start),
  .completed(completed),.rejected(rejected),.last_sequence(capture_sequence),.last_crc(capture_crc),.fault(schedule_fault),
  .capture_active(active),.result_done(result_done),.result_error(|result_fault),
  .m_axi_awaddr(m_axi_control_awaddr),
  .m_axi_awprot(m_axi_control_awprot),
  .m_axi_awvalid(m_axi_control_awvalid),
  .m_axi_awready(m_axi_control_awready),
  .m_axi_wdata(m_axi_control_wdata),
  .m_axi_wstrb(m_axi_control_wstrb),
  .m_axi_wvalid(m_axi_control_wvalid),
  .m_axi_wready(m_axi_control_wready),
  .m_axi_bresp(m_axi_control_bresp),
  .m_axi_bvalid(m_axi_control_bvalid),
  .m_axi_bready(m_axi_control_bready),
  .m_axi_araddr(m_axi_control_araddr),
  .m_axi_arprot(m_axi_control_arprot),
  .m_axi_arvalid(m_axi_control_arvalid),
  .m_axi_arready(m_axi_control_arready),
  .m_axi_rdata(m_axi_control_rdata),
  .m_axi_rresp(m_axi_control_rresp),
  .m_axi_rvalid(m_axi_control_rvalid),
  .m_axi_rready(m_axi_control_rready));
 pl_result_latch #(.PIXELS(ROI_WIDTH*ROI_HEIGHT)) latch(
  .clk(control_clk),.resetn(control_resetn),.request(publish),.busy(result_busy),.done(result_done),.fault(result_fault),
  .frame_sequence(core_sequence),.peak(peak),.threshold(threshold),.mask_pixels(mask_pixels),.alarm(result_alarm),.valid(result_valid),
  .m_axi_araddr(m_axi_result_araddr),
  .m_axi_arlen(m_axi_result_arlen),
  .m_axi_arsize(m_axi_result_arsize),
  .m_axi_arburst(m_axi_result_arburst),
  .m_axi_arvalid(m_axi_result_arvalid),
  .m_axi_arready(m_axi_result_arready),
  .m_axi_rdata(m_axi_result_rdata),
  .m_axi_rresp(m_axi_result_rresp),
  .m_axi_rlast(m_axi_result_rlast),
  .m_axi_rvalid(m_axi_result_rvalid),
  .m_axi_rready(m_axi_result_rready));
endmodule
