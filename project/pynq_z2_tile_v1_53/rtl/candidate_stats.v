// One full-frame global candidate region, independent of display mode.
// Snapshot sequence persists across pixel resets; stale snapshots are detectable.
module candidate_stats #(parameter WIDTH=1280,HEIGHT=720)(
 input wire clk,control_clk,reset,de,vs,mask,input wire [31:0] config_word,
 output wire [31:0] count_ref,min_ref,max_ref,seq_ref,config_ref,status_ref,crc_ref);
 reg pd=0,pv=0,started=0;reg [15:0] x=0,y=0;
 reg [31:0] crc=32'hffffffff;
 reg [31:0] pixels=0,count=0,frame_config=0,sequence_id=0;
 reg [15:0] xmin=0,ymin=0,xmax=0,ymax=0;
 reg [223:0] completed=0;reg publish=0;
 // Conservative engineering gate, not a trained crack classifier.
 wire tile_alarm=frame_config[17:16]==3 && count>=32 &&
                 ((xmax-xmin)>=23 || (ymax-ymin)>=23);
 always @(posedge clk)begin
  publish<=0;
  if(reset)begin
   pd<=0;pv<=0;started<=0;x<=0;y<=0;pixels<=0;count<=0;crc<=32'hffffffff;
   xmin<=0;ymin<=0;xmax<=0;ymax<=0;frame_config<=0;
  end else begin
   pd<=de;pv<=vs;
   if(vs && !pv)begin
    if(started && pixels==WIDTH*HEIGHT)begin
     sequence_id<=sequence_id+1'b1;
     completed<={~crc,(count!=0?32'd3:32'd1)|(tile_alarm?32'd4:32'd0),frame_config,sequence_id+32'd1,
                 count!=0?{ymax,xmax}:32'd0,count!=0?{ymin,xmin}:32'd0,count};
     publish<=1;
    end
    started<=1;x<=0;y<=0;pixels<=0;count<=0;crc<=32'hffffffff;xmin<=0;ymin<=0;xmax<=0;ymax<=0;
   end else begin
    if(de)begin
     // Row-major effective pixels, LSB-first CRC-32/ISO-HDLC bit recurrence.
     crc<=(crc>>1)^((crc[0]^mask)?32'hedb88320:32'd0);
     x<=x+1'b1;pixels<=pixels+1'b1;
     if(pixels==0)frame_config<=config_word;
     if(mask && x<WIDTH && y<HEIGHT)begin
      count<=count+1'b1;
      if(count==0)begin xmin<=x;xmax<=x;ymin<=y;ymax<=y;end
      else begin
       if(x<xmin)xmin<=x;if(x>xmax)xmax<=x;
       if(y<ymin)ymin<=y;if(y>ymax)ymax<=y;
      end
     end
    end else x<=0;
    if(pd && !de)y<=y+1'b1;
   end
  end
 end
 // Latest completed frame may replace a pending frame, but held never changes
 // during a transfer. At 60Hz and 200MHz control clock every frame is delivered.
 reg [223:0] pending=0,held=0;reg pending_valid=0,send=0;wire received;
 always @(posedge clk)begin
  if(send && received)send<=0;
  if(!send && !received && pending_valid)begin held<=pending;send<=1;pending_valid<=0;end
  if(publish)begin pending<=completed;pending_valid<=1;end
 end
 wire [223:0] snapshot;
 xpm_cdc_handshake #(.DEST_EXT_HSK(0),.DEST_SYNC_FF(4),.SRC_SYNC_FF(4),.WIDTH(224),.INIT_SYNC_FF(1))
 transfer(.src_clk(clk),.src_in(held),.src_send(send),.src_rcv(received),
 .dest_clk(control_clk),.dest_out(snapshot),.dest_req(),.dest_ack(1'b0));
 assign {crc_ref,status_ref,config_ref,seq_ref,max_ref,min_ref,count_ref}=snapshot;
endmodule
