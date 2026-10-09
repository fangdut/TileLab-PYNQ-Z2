// Coherent frame-count snapshot. Handshake supports arbitrary jumps on video reset.
module status_cdc(input wire pixel_clk,ref_clk,locked,sink_hpd,format_ok,
 input wire [31:0] frame_count, output wire [31:0] frame_count_ref,
 output wire [3:0] led, output wire source_hpd);
 reg send=0; wire received;
 always @(posedge pixel_clk) begin
  if(!send && !received) send<=1;
  else if(send && received) send<=0;
 end
 xpm_cdc_handshake #(.DEST_EXT_HSK(0),.DEST_SYNC_FF(4),.SRC_SYNC_FF(4),.WIDTH(32),.INIT_SYNC_FF(1))
 snapshot(.src_clk(pixel_clk),.src_in(frame_count),.src_send(send),.src_rcv(received),
 .dest_clk(ref_clk),.dest_out(frame_count_ref),.dest_req(),.dest_ack(1'b0));
 wire lock_ref,hpd_ref,fmt_ref;
 xpm_cdc_single #(.DEST_SYNC_FF(4),.INIT_SYNC_FF(1),.SRC_INPUT_REG(0))
 lock_sync(.src_clk(1'b0),.src_in(locked),.dest_clk(ref_clk),.dest_out(lock_ref));
 xpm_cdc_single #(.DEST_SYNC_FF(4),.INIT_SYNC_FF(1),.SRC_INPUT_REG(0))
 // PYNQ-Z2 R19 is HDMI_TX_HPDN: Q8 inverts HDMI connector pin 19.
 // Low at the FPGA means a connected sink. Normalize before synchronizing.
 hpd_sync(.src_clk(1'b0),.src_in(~sink_hpd),.dest_clk(ref_clk),.dest_out(hpd_ref));
 xpm_cdc_single #(.DEST_SYNC_FF(4),.INIT_SYNC_FF(1),.SRC_INPUT_REG(0))
 fmt_sync(.src_clk(1'b0),.src_in(format_ok),.dest_clk(ref_clk),.dest_out(fmt_ref));
 assign source_hpd=hpd_ref;
 assign led={fmt_ref && lock_ref,frame_count_ref[5] && lock_ref,hpd_ref,lock_ref};
endmodule
