// V0.4 fixed raster: 720p60. All display modes have identical latency.
// Native Digilent RBG -> RGB AXIS gray -> 2-row window -> 3-stage Sobel.
// Window bottom-right at (x,y) belongs to center (x-1,y-1).
// Original RGB, mode and ALL timing are delayed one full line+one pixel,
// plus the six arithmetic/window pipeline stages. Stats adds one more stage.
module video_core #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650)(
 input wire pixel_clk,control_clk,reset,input wire [1:0] mode_request,
 input wire [23:0] rgb_in,input wire de_in,hs_in,vs_in,
 output reg [7:0] gray_out=0,edge_out=0,smooth_out=0,
 output wire [23:0] rgb_out,output wire de_out,hs_out,vs_out,
 output wire [31:0] frame_count,frame_pixels,
 output wire [15:0] frame_lines,line_pixels,output wire format_ok,
 output reg [1:0] mode_active=0,output wire pixel_reset,window_valid);
 xpm_cdc_async_rst #(.DEST_SYNC_FF(4),.INIT_SYNC_FF(1),.RST_ACTIVE_HIGH(1))
 reset_bridge(.src_arst(reset),.dest_clk(pixel_clk),.dest_arst(pixel_reset));
 // Two mode bits cross as one coherent transaction, never independent bit syncs.
 reg send=0;wire received;wire [1:0] mode_sync;
 always @(posedge control_clk) begin
  if(!send && !received) send<=1;
  else if(send && received) send<=0;
 end
 xpm_cdc_handshake #(.DEST_EXT_HSK(0),.DEST_SYNC_FF(4),.SRC_SYNC_FF(4),.WIDTH(2),.INIT_SYNC_FF(1))
 mode_bridge(.src_clk(control_clk),.src_in(mode_request),.src_send(send),.src_rcv(received),
 .dest_clk(pixel_clk),.dest_out(mode_sync),.dest_req(),.dest_ack(1'b0));
 reg prev_vs=0,prev_de=0,sof_pending=1;reg [15:0] x=0,y=0,xq=0,yq=0;
 always @(posedge pixel_clk) begin
  if(pixel_reset) begin
   prev_vs<=0;prev_de<=0;sof_pending<=1;x<=0;y<=0;xq<=0;yq<=0;mode_active<=0;
  end else begin
   prev_vs<=vs_in;prev_de<=de_in;xq<=x;yq<=y;
   if(vs_in && !prev_vs) begin
    sof_pending<=1;x<=0;y<=0;
    mode_active<=mode_sync;
   end else begin
    if(de_in) begin sof_pending<=0;x<=x+1'b1;end else x<=0;
    if(prev_de && !de_in) y<=y+1'b1;
   end
  end
 end
 wire [23:0] axis_rgb;wire axis_valid,axis_ready,axis_sof,axis_eol;
 axis_gray gray(.aclk(pixel_clk),.aresetn(!pixel_reset),.mode(1'b1),
 .s_axis_tdata({rgb_in[23:16],rgb_in[7:0],rgb_in[15:8]}),
 .s_axis_tvalid(de_in),.s_axis_tready(axis_ready),.s_axis_tuser(sof_pending),.s_axis_tlast(x==WIDTH-1),
 .m_axis_tdata(axis_rgb),.m_axis_tvalid(axis_valid),.m_axis_tready(1'b1),
 .m_axis_tuser(axis_sof),.m_axis_tlast(axis_eol));
 wire [71:0] win;wire wb;wire [15:0] wx,wy;
 window3x3 #(.WIDTH(WIDTH)) windows(.clk(pixel_clk),.reset(pixel_reset),.ce(1'b1),
 .in_valid(axis_valid),.pixel_in(axis_rgb[7:0]),.in_x(xq),.in_y(yq),
 .out_valid(window_valid),.out_x(wx),.out_y(wy),.window(win),.border(wb));
 wire sobel_valid;wire [7:0] edge_value;wire [10:0] magnitude;
 sobel3x3 sobel(.clk(pixel_clk),.reset(pixel_reset),.ce(1'b1),
 .in_valid(window_valid),.border(wb),.window(win),.out_valid(sobel_valid),
 .edge_pixel(edge_value),.magnitude(magnitude));
 wire gaussian_valid;wire [7:0] smooth_value;
 gaussian3x3 gaussian(.clk(pixel_clk),.reset(pixel_reset),.ce(1'b1),
 .in_valid(window_valid),.border(wb),.window(win),
 .out_valid(gaussian_valid),.pixel_out(smooth_value));
 // 29 bits: frame-applied mode, VS, HS, DE, native RBG. Ring memory is BRAM.
 wire [28:0] delayed;reg [28:0] tail[0:5];integer k;
 raster_delay #(.WIDTH(29),.WORDS(H_TOTAL)) alignment(.clk(pixel_clk),.reset(pixel_reset),
 .din({mode_active,vs_in,hs_in,de_in,rgb_in}),.dout(delayed));
 always @(posedge pixel_clk) begin
  if(pixel_reset) for(k=0;k<6;k=k+1) tail[k]<=0;
  else begin tail[0]<=delayed;for(k=1;k<6;k=k+1) tail[k]<=tail[k-1];end
 end
 // Delayed original is also used for gray mode: all modes preserve center position.
 wire [23:0] center=tail[5][23:0];
 wire [15:0] center_sum=16'd77*center[23:16]+16'd150*center[7:0]+16'd29*center[15:8];
 wire [7:0] shown_edge=sobel_valid?edge_value:8'b0;
 wire [23:0] selected=(tail[5][28:27]==1)?{3{center_sum[15:8]}}:
                          (tail[5][28:27]==2)?{3{shown_edge}}:
                          (tail[5][28:27]==3)?{3{gaussian_valid?smooth_value:8'b0}}:center;
 // Invalid windows become zero; delayed DE still emits full WIDTH x HEIGHT,
 // including right/bottom border pixels during the source's blanking intervals.
 always @(posedge pixel_clk) begin
  if(pixel_reset) begin gray_out<=0;edge_out<=0;smooth_out<=0;end
  else begin gray_out<=center_sum[15:8];edge_out<=shown_edge;smooth_out<=gaussian_valid?smooth_value:0;end
 end
 video_stats stats(.pixel_clk(pixel_clk),.reset(pixel_reset),.rgb_in(selected),
 .de_in(tail[5][24]),.hs_in(tail[5][25]),.vs_in(tail[5][26]),
 .rgb_out(rgb_out),.de_out(de_out),.hs_out(hs_out),.vs_out(vs_out),
 .frame_count(frame_count),.frame_pixels(frame_pixels),.frame_lines(frame_lines),
 .line_pixels(line_pixels),.format_ok(format_ok));
endmodule
