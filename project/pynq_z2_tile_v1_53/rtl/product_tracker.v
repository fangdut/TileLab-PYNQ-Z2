// One lane; a bright surface crosses the center-column gate. Two valid clear observations
// separate products. Touching products need an external trigger in future.
// Only PL image statistics determine IDs and best-frame ranking.
module product_tracker #(parameter CENTER_SUM=1279, MIN_GATE=200)(
 input wire clk,reset,frame_valid,
 input wire [15:0] gate_pixels,surface_xmin,surface_xmax,
 input wire [31:0] candidate_count,region_status,
 output reg decision_valid=0,
 output reg [31:0] product_id=0,flags=0,score=0);
 reg live=0;reg [1:0] quiet=0;reg [31:0] serial=0,best_area=0;
 reg [16:0] best_distance=17'h1ffff;
 reg best_complete=0;
 wire present=gate_pixels>=MIN_GATE;
 wire alarm=(region_status[3:0]!=0 || region_status[8]) && !region_status[31];
 wire [16:0] middle_sum={1'b0,surface_xmin}+{1'b0,surface_xmax};
 wire [16:0] distance=middle_sum>CENTER_SUM?middle_sum-CENTER_SUM:CENTER_SUM-middle_sum;
 wire complete_surface=surface_xmin>80 && surface_xmax<CENTER_SUM-80;
 // V1.5: after the surface is fully visible, choose the most centered alarm
 // frame. Compression/texture fluctuations must not favor an off-center frame
 // merely because it contains a few more candidate pixels. Partial-only
 // fallback still favors candidate coverage. No new clock or frame stall.
 wire centered_better=distance<best_distance || (distance==best_distance && candidate_count>best_area);
 wire partial_better=candidate_count>best_area || (candidate_count==best_area && distance<best_distance);
 wire better=alarm && (!live || (complete_surface && !best_complete) ||
   (complete_surface==best_complete && (complete_surface?centered_better:partial_better)));
 always @(posedge clk)begin
  decision_valid<=0;
  // FPGA configuration initializes serial; a video reset must not reuse IDs.
  if(reset)begin live<=0;quiet<=0;product_id<=0;flags<=0;score<=0;best_area<=0;best_distance<=17'h1ffff;best_complete<=0;end
  else if(frame_valid)begin
   // V1.5 trailer word 39: complete flag + twice the center distance.
   // Candidate area is already available independently in trailer word 3.
   // V1.42: invalid/partial captures are unknown observations. Complete the
   // decision handshake so capture can emit its invalid packet, but do not
   // start/end a product, consume a serial number or change its best frame.
   decision_valid<=1;flags<=0;product_id<=live?serial:0;
   if(!region_status[31])begin
    score<={complete_surface,14'b0,distance};
    if(present)begin
    quiet<=0;live<=1;
    if(!live)begin serial<=serial+1'b1;product_id<=serial+1'b1;best_area<=0;best_distance<=17'h1ffff;best_complete<=0;end
    flags<=32'h1|(!live?32'h2:0)|(better?32'h8:0)|(!region_status[31]?32'h10:0);
    if(better)begin best_area<=candidate_count;best_distance<=distance;best_complete<=complete_surface;end
    end else if(live)begin
    if(quiet==1)begin flags<=32'h4;live<=0;quiet<=0;end
    else quiet<=quiet+1'b1;
    end
   end
  end
 end
endmodule
