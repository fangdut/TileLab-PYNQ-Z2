// Research candidate. Legacy features and learned score have identical fixed latency.
module boost_frontend_v156 #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650)(
 input wire clk,reset,input wire [7:0] gray,input wire [23:0] rgb,input wire de,hs,vs,
 output wire [23:0] rgb_out,output wire de_out,hs_out,vs_out,
 output wire [7:0] score,score_wide,score_short,score_long,score_wide_line,
 output wire [3:0] direction_weak,output wire signed [31:0] model_score,output wire model_valid);
 wire [23:0] rgb0;wire de0,hs0,vs0;wire [7:0] n,w,s,l,line;wire [3:0] directions;
 wire [111:0] features;wire feature_valid;
 boost_feature_frontend_v156 #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.H_TOTAL(H_TOTAL)) features_window(
 .clk(clk),.reset(reset),.gray(gray),.rgb(rgb),.de(de),.hs(hs),.vs(vs),
 .rgb_out(rgb0),.de_out(de0),.hs_out(hs0),.vs_out(vs0),.score(n),.score_wide(w),.score_short(s),.score_long(l),.score_wide_line(line),
 .direction_weak(directions),.feature_packet(features),.feature_valid(feature_valid));
 pixel_boost_v159 classifier(.clk(clk),.reset(reset),.valid_in(feature_valid),.features(features),.score(model_score),.valid_out(model_valid));
 reg [70:0] aligned[0:8];integer k;
 always @(posedge clk)begin
  if(reset)for(k=0;k<9;k=k+1)aligned[k]<=0;
  else begin aligned[0]<={vs0,hs0,de0,rgb0,n,w,s,l,line,directions};for(k=1;k<9;k=k+1)aligned[k]<=aligned[k-1];end
 end
 assign {vs_out,hs_out,de_out,rgb_out,score,score_wide,score_short,score_long,score_wide_line,direction_weak}=aligned[8];
endmodule
