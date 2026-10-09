// CPU writes ROI first, then toggles bit31 to commit an immutable CDC payload.
module config_bridge(input wire control_clk,pixel_clk,
 input wire [31:0] config_request,roi_min_request,roi_max_request,
 output wire [95:0] pixel_config);
 reg seen=0,send=0;reg [95:0] held=0;wire received;
 always @(posedge control_clk) begin
  if(send && received) send<=0;
  else if(!send && !received && config_request[31]!=seen) begin
   held<={roi_max_request,roi_min_request,config_request};
   seen<=config_request[31];send<=1;
  end
 end
 xpm_cdc_handshake #(.DEST_EXT_HSK(0),.DEST_SYNC_FF(4),.SRC_SYNC_FF(4),.WIDTH(96),.INIT_SYNC_FF(1))
 transfer(.src_clk(control_clk),.src_in(held),.src_send(send),.src_rcv(received),
 .dest_clk(pixel_clk),.dest_out(pixel_config),.dest_req(),.dest_ack(1'b0));
endmodule
