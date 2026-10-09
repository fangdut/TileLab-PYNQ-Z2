// Continuous packets: B,G,R,mask pixels followed by 40 metadata words.
// TLAST follows metadata. SG DMA buffers are prepared before frames arrive.
// No per-frame ARM trigger. Backpressure invalidates the packet explicitly.
module frame_capture #(parameter WIDTH=1280,HEIGHT=720)(
 (* X_INTERFACE_PARAMETER="XIL_INTERFACENAME pixel_clk, ASSOCIATED_BUSIF M_AXIS, FREQ_HZ 100000000" *)
 (* X_INTERFACE_INFO="xilinx.com:signal:clock:1.0 pixel_clk CLK" *) input wire pixel_clk,
 input wire control_clk,reset,input wire [31:0] request,
 input wire [23:0] rgb,input wire de,vs,mask,input wire [31:0] config_word,
 input wire [511:0] region_boxes,input wire [255:0] region_areas,
 input wire [31:0] region_seq,region_status,
 (* X_INTERFACE_INFO="xilinx.com:interface:axis:1.0 M_AXIS TDATA" *) output reg [31:0] m_axis_tdata=0,
 (* X_INTERFACE_INFO="xilinx.com:interface:axis:1.0 M_AXIS TVALID" *) output reg m_axis_tvalid=0,
 (* X_INTERFACE_INFO="xilinx.com:interface:axis:1.0 M_AXIS TREADY" *) input wire m_axis_tready,
 (* X_INTERFACE_INFO="xilinx.com:interface:axis:1.0 M_AXIS TLAST" *) output reg m_axis_tlast=0,
 output wire [31:0] cap_seq,cap_count,cap_min,cap_max,cap_status,cap_config);
 wire enabled;
 xpm_cdc_single #(.DEST_SYNC_FF(4),.INIT_SYNC_FF(1),.SRC_INPUT_REG(0)) enable_cdc(
 .src_clk(control_clk),.src_in(request[1]),.dest_clk(pixel_clk),.dest_out(enabled));
 localparam IDLE=0,PIXELS=1,REGIONS=2,DECISION=3,TRAILER=4,META_CRC=5;
 reg [2:0] state=IDLE;reg pv=0,pd=0,bad=0;
 // A region result may arrive after VS but before the next active raster.
 // Keep that VS's start opportunity while the old packet finishes. Once DE
 // has begun, the window stays closed through every horizontal blank; never
 // begin a partial frame. frame_id is the epoch of the latest observed VS.
 reg pending_frame=0;
 reg [15:0] x=0,y=0,xmin=0,xmax=0,ymin=0,ymax=0;
 reg [15:0] gate_count=0,surface_min=0,surface_max=0;
 reg [31:0] frame_id=0,count=0,pixels=0,seq=0,cfg=0;
 // IEEE CRC-32 of little-endian B,G,R,mask bytes, before DDR/ARM/TCP.
 // Unrolled fixed 32-bit XOR network: one pixel per clock, no frame buffer.
 reg [31:0] frame_crc=32'hffffffff;
 wire [31:0] pixel_word={{7'b0,mask},rgb[23:16],rgb[7:0],rgb[15:8]};
 function [31:0] crc32_word;
  input [31:0] crc,data;
  reg [31:0] c;integer b;
  begin
   c=crc^data;
   for(b=0;b<32;b=b+1)c=(c>>1)^({32{c[0]}}&32'hedb88320);
   crc32_word=c;
  end
 endfunction
 reg [31:0] meta[0:39];reg [5:0] trailer_index=0;
 // Reuse the pixel CRC state/XOR network during vertical blanking. Word 8
 // is zero while calculating and carries the result on the AXIS stream.
 // No additional stream words or per-pixel cycles are introduced.
 // META_CRC and TRAILER never overlap. Reuse their address counter and
 // one read mux; no second 40-word register-array read port is needed.
 wire [31:0] descriptor_word=meta[trailer_index];
 wire [31:0] crc_word=state==META_CRC?(trailer_index==8?32'b0:descriptor_word):pixel_word;
 wire [31:0] crc_next=crc32_word(frame_crc,crc_word);
 reg decide=0;wire decision_valid;wire [31:0] product_id,product_flags,product_score;
 wire [9:0] luma={2'b0,rgb[23:16]}+{1'b0,rgb[7:0],1'b0}+{2'b0,rgb[15:8]};
 // V1.37: optional low-light product presence; independent of crack threshold.
 // cfg is latched for the frame (at its first pixel, before this x>=80 ROI).
 wire [9:0] surface_threshold=cfg[26]?10'd160:10'd320;
 wire surface=de && x>=80 && x<WIDTH-80 && y>=110 && y<HEIGHT-110 && luma>=surface_threshold;
 // A single center column can disappear inside a vertical crack, falsely
 // splitting one physical tile. Integrate a 64-pixel band at full resolution.
 // 64*500=32000 fits gate_count; the required average bright height stays 200.
 // Compact simulation geometries retain their original one-column gate.
 localparam GATE_WIDTH=(HEIGHT>400)?64:1;
 wire inside_gate=x>=WIDTH/2-GATE_WIDTH/2 && x<WIDTH/2+(GATE_WIDTH+1)/2;
 wire accept_pixel=de && x<WIDTH && y<HEIGHT;
 wire last_pixel=accept_pixel && x==WIDTH-1 && y==HEIGHT-1;
 wire drop_pixel=m_axis_tvalid && !m_axis_tready;
 wire [31:0] next_count=count+(mask?32'd1:32'd0);
 wire [15:0] nxmin=mask && (count==0 || x<xmin)?x:xmin;
 wire [15:0] nxmax=mask && (count==0 || x>xmax)?x:xmax;
 wire [15:0] nymin=mask && (count==0 || y<ymin)?y:ymin;
 wire [15:0] nymax=mask && (count==0 || y>ymax)?y:ymax;
 product_tracker #(.CENTER_SUM(WIDTH-1),.MIN_GATE(HEIGHT>400?200*GATE_WIDTH:4)) products(
 .clk(pixel_clk),.reset(reset),.frame_valid(decide),.gate_pixels(gate_count),
 .surface_xmin(surface_min),.surface_xmax(surface_max),.candidate_count(count),
 .region_status(meta[9]),.decision_valid(decision_valid),.product_id(product_id),.flags(product_flags),.score(product_score));
 integer i;
 reg [191:0] completed=0,held=0;reg publish=0,send=0;wire received;
 always @(posedge pixel_clk)begin
  decide<=0;publish<=0;
  if(m_axis_tvalid && m_axis_tready)begin m_axis_tvalid<=0;m_axis_tlast<=0;end
  // Keep the frame epoch across video reset, matching region_grid's counter.
  if(reset)begin state<=IDLE;pending_frame<=0;pv<=0;pd<=0;x<=0;y<=0;bad<=0;m_axis_tvalid<=0;m_axis_tlast<=0;count<=0;pixels<=0;gate_count<=0;frame_crc<=32'hffffffff;end
  else begin
   pv<=vs;pd<=de;
   if(vs && !pv)begin
    frame_id<=frame_id+1'b1;x<=0;y<=0;
    pending_frame<=enabled;
    if(state==PIXELS)begin bad<=1;state<=REGIONS;end
   end else begin
    if(de)x<=x+1'b1;else x<=0;
    if(pd && !de)y<=y+1'b1;
   end
   if(de)pending_frame<=0;
   // m_axis_tvalid must be clear: IDLE alone does not mean that the old
   // TLAST word has been accepted. Do not reset its CRC/statistics earlier.
   if(state==IDLE && enabled && !de && !m_axis_tvalid &&
      (pending_frame || (vs && !pv)))begin
    pending_frame<=0;state<=PIXELS;seq<=vs && !pv?frame_id+1'b1:frame_id;
    bad<=0;count<=0;pixels<=0;cfg<=config_word;frame_crc<=32'hffffffff;
    xmin<=0;xmax<=0;ymin<=0;ymax<=0;gate_count<=0;surface_min<=16'hffff;surface_max<=0;
   end
   if(state==PIXELS && accept_pixel)begin
    frame_crc<=crc_next;
    pixels<=pixels+1'b1;count<=next_count;xmin<=nxmin;xmax<=nxmax;ymin<=nymin;ymax<=nymax;
    if(pixels==0)cfg<=config_word;
    if(surface)begin
     if(x<surface_min)surface_min<=x;if(x>surface_max)surface_max<=x;
     if(inside_gate)gate_count<=gate_count+1'b1;
    end
    if(drop_pixel)bad<=1;
    else begin m_axis_tdata<=pixel_word;m_axis_tvalid<=1;m_axis_tlast<=0;end
    if(last_pixel)begin state<=REGIONS;bad<=bad|drop_pixel|(pixels!=WIDTH*HEIGHT-1);end
   end
   // VS begins vertical blanking, not the next pixel payload. Allow the
   // previous frame's bounded region computation to finish across VS. If a
   // new epoch's active pixels arrive first, terminate the old packet as
   // invalid; the closed pending window prevents a mid-frame restart.
   if(state==REGIONS && (region_seq==seq || (de && frame_id!=seq)))begin
    for(i=0;i<40;i=i+1)meta[i]<=0;
    // New magic prevents a new firmware from claiming CRC on old hardware.
    meta[0]<=32'h54465337;meta[1]<=~frame_crc;meta[2]<=seq;meta[3]<=count;
    meta[4]<=count?{ymin,xmin}:0;meta[5]<=count?{ymax,xmax}:0;
    meta[6]<={bad|region_seq!=seq,27'b0,(region_status[3:0]!=0 || region_status[8]),1'b1,2'b0};
    meta[7]<=cfg;meta[9]<=region_seq==seq?(region_status|(bad?32'h80000000:0)):32'h80000000;
    for(i=0;i<16;i=i+1)meta[10+i]<=region_boxes[i*32+:32];
    for(i=0;i<8;i=i+1)meta[26+i]<=region_areas[i*32+:32];
    meta[35]<=WIDTH*HEIGHT*4;decide<=1;state<=DECISION;
   end
   if(state==DECISION && decision_valid)begin
    meta[37]<=product_id;meta[38]<=product_flags;meta[39]<=product_score;
    frame_crc<=32'hffffffff;trailer_index<=0;state<=META_CRC;
    completed<={meta[7],meta[6],meta[5],meta[4],meta[3],meta[2]};publish<=1;
   end
   if(state==META_CRC)begin
    frame_crc<=crc_next;
    if(trailer_index==39)begin
     meta[8]<=~crc_next;trailer_index<=0;state<=TRAILER;
    end else trailer_index<=trailer_index+1'b1;
   end
   if(state==TRAILER && (!m_axis_tvalid || m_axis_tready))begin
    m_axis_tdata<=descriptor_word;m_axis_tvalid<=1;m_axis_tlast<=trailer_index==39;
    if(trailer_index==39)state<=IDLE;else trailer_index<=trailer_index+1'b1;
   end
  end
 end
 always @(posedge pixel_clk)begin
  if(send && received)send<=0;
  if(publish && !send && !received)begin held<=completed;send<=1;end
 end
 wire [191:0] snapshot;
 xpm_cdc_handshake #(.DEST_EXT_HSK(0),.DEST_SYNC_FF(4),.SRC_SYNC_FF(4),.WIDTH(192),.INIT_SYNC_FF(1)) transfer(
 .src_clk(pixel_clk),.src_in(held),.src_send(send),.src_rcv(received),.dest_clk(control_clk),.dest_out(snapshot),.dest_req(),.dest_ack(1'b0));
 assign {cap_config,cap_status,cap_max,cap_min,cap_count,cap_seq}=snapshot;
endmodule
