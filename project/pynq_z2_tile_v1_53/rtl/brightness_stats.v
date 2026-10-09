// Raw grayscale ROI sum and count before threshold/morphology.
// No image work is performed in PS. Sum <= 921600*255 = 235008000 for 720p.
module brightness_stats #(parameter WIDTH=1280,HEIGHT=720)(
 input wire clk,control_clk,reset,de,vs,include_pixel,input wire [7:0] gray,
 input wire [31:0] config_word,roi_min,roi_max,
 output wire [31:0] count_ref,sum_ref,seq_ref,config_ref,min_ref,max_ref);
 reg pv=0,started=0;reg [31:0] pixels=0,count=0,total=0,sequence_id=0;
 reg [31:0] frame_config=0,frame_min=0,frame_max=0;
 reg [191:0] completed=0;reg publish=0;
 always @(posedge clk)begin
  publish<=0;
  if(reset)begin
   pv<=0;started<=0;pixels<=0;count<=0;total<=0;
   frame_config<=0;frame_min<=0;frame_max<=0;
  end else begin
   pv<=vs;
   if(vs && !pv)begin
    if(started && pixels==WIDTH*HEIGHT)begin
     sequence_id<=sequence_id+1'b1;
     completed<={frame_max,frame_min,frame_config,sequence_id+32'd1,total,count};
     publish<=1;
    end
    started<=1;pixels<=0;count<=0;total<=0;
   end else if(de)begin
    pixels<=pixels+1'b1;
    if(pixels==0)begin frame_config<=config_word;frame_min<=roi_min;frame_max<=roi_max;end
    if(include_pixel)begin count<=count+1'b1;total<=total+{24'b0,gray};end
   end
  end
 end
 reg [191:0] pending=0,held=0;reg pending_valid=0,send=0;wire received;
 always @(posedge clk)begin
  if(send && received)send<=0;
  if(!send && !received && pending_valid)begin held<=pending;send<=1;pending_valid<=0;end
  if(publish)begin pending<=completed;pending_valid<=1;end
 end
 wire [191:0] snapshot;
 xpm_cdc_handshake #(.DEST_EXT_HSK(0),.DEST_SYNC_FF(4),.SRC_SYNC_FF(4),.WIDTH(192),.INIT_SYNC_FF(1))
 transfer(.src_clk(clk),.src_in(held),.src_send(send),.src_rcv(received),
 .dest_clk(control_clk),.dest_out(snapshot),.dest_req(),.dest_ack(1'b0));
 assign {max_ref,min_ref,config_ref,seq_ref,sum_ref,count_ref}=snapshot;
endmodule
