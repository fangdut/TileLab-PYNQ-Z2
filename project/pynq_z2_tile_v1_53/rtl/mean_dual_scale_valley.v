// V1.52: two contrast scales, aligned to the same input pixel.
// Radius-8 remains the sole strong-seed feature. Radius-16 is optional weak
// support downstream. Keeping independent windows preserves radius-8 border
// behavior: a wider window must not erase valid narrow scores near frame edges.
module mean_dual_scale_valley #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650)(
 input wire clk,reset,input wire [7:0] gray,
 input wire [23:0] rgb,input wire de,hs,vs,
 output wire [23:0] rgb_out,output wire de_out,hs_out,vs_out,
 output wire [7:0] score,score_wide,score_short,score_long);
 wire [7:0] score_narrow,mean_narrow;
 directional_mean_valley #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.H_TOTAL(H_TOTAL),.R(8)) narrow(
  .clk(clk),.reset(reset),.gray(gray),.rgb(rgb),.de(de),.hs(hs),.vs(vs),
  .rgb_out(),.de_out(),.hs_out(),.vs_out(),.score(score_narrow),.mean_score(mean_narrow));
 directional_mean_valley #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.H_TOTAL(H_TOTAL),.R(16)) wide(
  .clk(clk),.reset(reset),.gray(gray),.rgb(rgb),.de(de),.hs(hs),.vs(vs),
  .rgb_out(rgb_out),.de_out(de_out),.hs_out(hs_out),.vs_out(vs_out),.score(score_wide),.mean_score(score_long));
 // Difference between window latencies is 8*H_TOTAL+8. An intervening
 // raster_delay samples the prior score register, adding WORDS+1 clocks.
 raster_delay #(.WIDTH(16),.WORDS(8*H_TOTAL+7)) narrow_align(
  .clk(clk),.reset(reset),.din({mean_narrow,score_narrow}),.dout({score_short,score}));
endmodule
