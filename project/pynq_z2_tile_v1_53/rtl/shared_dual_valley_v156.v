// Identical external feature contract/latency; eliminates duplicate 16-row R8 storage.
module shared_dual_valley_v156 #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650)(
 input wire clk,reset,input wire [7:0] gray,input wire [23:0] rgb,input wire de,hs,vs,
 output wire [23:0] rgb_out,output wire de_out,hs_out,vs_out,
 output wire [7:0] score,score_wide,score_short,score_long,score_wide_line,output wire [3:0] direction_weak);
 wire [7:0] narrow_score,narrow_mean;
 shared_window_v156 #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.H_TOTAL(H_TOTAL)) window(
 .clk(clk),.reset(reset),.gray(gray),.rgb(rgb),.de(de),.hs(hs),.vs(vs),
 .rgb_out(rgb_out),.de_out(de_out),.hs_out(hs_out),.vs_out(vs_out),.score(score_wide),.mean_score(score_long),
 .wide_line_score(score_wide_line),.direction_weak(direction_weak),.narrow_score(narrow_score),.short_score(narrow_mean));
 raster_delay #(.WIDTH(16),.WORDS(8*H_TOTAL+7)) narrow_align(
 .clk(clk),.reset(reset),.din({narrow_mean,narrow_score}),.dout({score_short,score}));
endmodule
