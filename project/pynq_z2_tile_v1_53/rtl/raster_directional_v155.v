// V1.55 bounded, direction-eligible support.
// Centered binary AND/OR. Both operations force the outer border black.
// Sideband/full raster delay: H_TOTAL+3 edge indices.
module raster_directional_v155 #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650,SIDE_WIDTH=28,BYPASS_WHEN_NOT_GROW=0)(
 input wire clk,reset,dilate,mask_in,de_in,hs_in,vs_in,
 input wire [SIDE_WIDTH-1:0] side_in,
 output reg mask_out=0,output wire de_out,hs_out,vs_out,
 output wire [SIDE_WIDTH-1:0] side_out,
 input wire grow,weak_in,output reg weak_out=0,
 input wire directional_grow,input wire [3:0] directions_in,output reg [3:0] directions_out=0);
 reg prev_de=0,prev_vs=0;reg [15:0] x=0,y=0;
 always @(posedge clk) begin
  if(reset)begin prev_de<=0;prev_vs<=0;x<=0;y<=0;end
  else begin
   prev_de<=de_in;prev_vs<=vs_in;
   if(vs_in && !prev_vs)begin x<=0;y<=0;end
   else begin
    if(de_in)x<=x+1'b1;else x<=0;
    if(prev_de && !de_in)y<=y+1'b1;
   end
  end
 end
 wire [71:0] w;wire valid,border;
 window3x3 #(.WIDTH(WIDTH)) win(.clk(clk),.reset(reset),.ce(1'b1),
 .in_valid(de_in),.pixel_in({2'b0,directions_in,weak_in,mask_in}),.in_x(x),.in_y(y),
 .out_valid(valid),.out_x(),.out_y(),.window(w),.border(border));
 wire [8:0] bits9={w[64],w[56],w[48],w[40],w[32],w[24],w[16],w[8],w[0]};
 // Local, bounded hysteresis: preserve a strong center; promote a weak center
 // only with >=3 accepted pixels in its 3x3 neighborhood. Two cascaded stages
 // extend at most two pixels and do not recursively flood an entire texture.
 wire [3:0] support_count={3'b0,bits9[0]}+{3'b0,bits9[1]}+{3'b0,bits9[2]}+
  {3'b0,bits9[3]}+{3'b0,bits9[4]}+{3'b0,bits9[5]}+
  {3'b0,bits9[6]}+{3'b0,bits9[7]}+{3'b0,bits9[8]};
 wire direction_hit=(w[34] && (w[40] || w[24])) ||
  (w[35] && (w[56] || w[8])) || (w[36] && (w[64] || w[0])) ||
  (w[37] && (w[48] || w[16]));
 always @(posedge clk)begin
  if(reset)begin mask_out<=0;weak_out<=0;directions_out<=0;end
  else begin
   weak_out<=valid && !border && w[33];
   directions_out<=(valid && !border)?w[37:34]:0;
   mask_out<=valid && !border && (grow?(w[32] || (w[33] && support_count>=3) || (directional_grow && direction_hit)):
     (BYPASS_WHEN_NOT_GROW?w[32]:(dilate?(|bits9):(&bits9))));
  end
 end
 wire [SIDE_WIDTH+2:0] delayed;reg [SIDE_WIDTH+2:0] q[0:2];integer k;
 raster_delay #(.WIDTH(SIDE_WIDTH+3),.WORDS(H_TOTAL)) align(.clk(clk),.reset(reset),
 .din({vs_in,hs_in,de_in,side_in}),.dout(delayed));
 always @(posedge clk)begin
  if(reset)for(k=0;k<3;k=k+1)q[k]<=0;
  else begin q[0]<=delayed;q[1]<=q[0];q[2]<=q[1];end
 end
 assign {vs_out,hs_out,de_out,side_out}=q[2];
endmodule
