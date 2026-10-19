// Identical external feature contract/latency; eliminates duplicate 16-row R8 storage.
module boost_feature_frontend_v156 #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650)(
 input wire clk,reset,input wire [7:0] gray,input wire [23:0] rgb,input wire de,hs,vs,
 output wire [23:0] rgb_out,output wire de_out,hs_out,vs_out,
 output wire [7:0] score,score_wide,score_short,score_long,score_wide_line,output wire [3:0] direction_weak,output wire [111:0] feature_packet,output wire feature_valid);
 wire [23:0] rgb_out_raw;wire de_out_raw,hs_out_raw,vs_out_raw;wire [7:0] score_raw,score_wide_raw,score_short_raw,score_long_raw,score_wide_line_raw;wire [3:0] direction_weak_raw;
 // Native HDMI bus is RBG; the model contract is RGB. Use the same
 // center-aligned pixel as the existing gray packet, without an extra stage.
 wire [15:0] chroma;
 color_opponent_pair color_pair(.rgb({rgb_out[23:16],rgb_out[7:0],rgb_out[15:8]}),.features(chroma));
 wire [87:0] hi;assign feature_packet={chroma,hi,score};
 wire [7:0] narrow_score,narrow_mean;
 boost_feature_window_v156 #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.H_TOTAL(H_TOTAL)) window(
 .clk(clk),.reset(reset),.gray(gray),.rgb(rgb),.de(de),.hs(hs),.vs(vs),
 .rgb_out(rgb_out_raw),.de_out(de_out_raw),.hs_out(hs_out_raw),.vs_out(vs_out_raw),.score(score_wide_raw),.mean_score(score_long_raw),
 .wide_line_score(score_wide_line_raw),.direction_weak(direction_weak_raw),.narrow_score(narrow_score),.short_score(narrow_mean),.features_hi(hi),.features_valid(feature_valid));
 raster_delay #(.WIDTH(16),.WORDS(8*H_TOTAL+7)) narrow_align(
 .clk(clk),.reset(reset),.din({narrow_mean,narrow_score}),.dout({score_short_raw,score_raw}));
reg [70:0] feature_align0=0,feature_align1=0;
 always @(posedge clk)begin
  if(reset)begin feature_align0<=0;feature_align1<=0;end
  else begin feature_align0<={vs_out_raw,hs_out_raw,de_out_raw,rgb_out_raw,score_raw,score_wide_raw,score_short_raw,score_long_raw,score_wide_line_raw,direction_weak_raw};feature_align1<=feature_align0;end
 end
 assign {vs_out,hs_out,de_out,rgb_out,score,score_wide,score_short,score_long,score_wide_line,direction_weak}=feature_align1;
endmodule
