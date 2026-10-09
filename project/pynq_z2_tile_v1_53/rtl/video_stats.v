// One pixel-clock pipeline stage. RGB and all sync signals have identical latency.
module video_stats(
 input wire pixel_clk, reset, input wire [23:0] rgb_in,
 input wire de_in, hs_in, vs_in,
 output reg [23:0] rgb_out, output reg de_out, hs_out, vs_out,
 output reg [31:0] frame_count=0, output reg [31:0] frame_pixels=0,
 output reg [15:0] frame_lines=0, line_pixels=0,
 output reg format_ok=0);
 reg prev_vs=0, prev_de=0, seen_frame=0;
 reg [31:0] pixels=0;
 reg [15:0] lines=0, width=0;
 reg bad_width=0;
 always @(posedge pixel_clk) begin
  if(reset) begin
   rgb_out<=0; de_out<=0; hs_out<=0; vs_out<=0;
   frame_count<=0; frame_pixels<=0; frame_lines<=0; line_pixels<=0;
   prev_vs<=0; prev_de<=0; seen_frame<=0; pixels<=0; lines<=0; width<=0;
   bad_width<=0; format_ok<=0;
  end else begin
   rgb_out<=rgb_in; de_out<=de_in; hs_out<=hs_in; vs_out<=vs_in;
   prev_vs<=vs_in; prev_de<=de_in;
   if (de_in) begin pixels<=pixels+1; width<=width+1; end
   if (prev_de && !de_in) begin
    line_pixels<=width; lines<=lines+1; width<=0;
    if(width!=1280) bad_width<=1;
   end
   if(vs_in && !prev_vs) begin
    if(seen_frame) begin
     frame_count<=frame_count+1; frame_pixels<=pixels; frame_lines<=lines;
     format_ok<=(pixels==921600 && lines==720 && !bad_width);
    end
    seen_frame<=1; pixels<=0; lines<=0; width<=0; bad_width<=0;
   end
  end
 end
endmodule
