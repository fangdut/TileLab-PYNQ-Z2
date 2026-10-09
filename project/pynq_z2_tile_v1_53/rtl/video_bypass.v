module video_bypass #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650)(
 input wire pixel_clk,control_clk,reset,
 input wire [31:0] config_request,roi_min_request,roi_max_request,
 input wire [23:0] rgb_in,input wire de_in,hs_in,vs_in,
 output wire [23:0] rgb_out,output wire de_out,hs_out,vs_out,
 output wire [31:0] frame_count,frame_pixels,
 output wire [15:0] frame_lines,line_pixels,output wire format_ok,
 output wire [2:0] mode_active,
 (* X_INTERFACE_PARAMETER="XIL_INTERFACENAME pixel_reset, POLARITY ACTIVE_HIGH" *)
 (* X_INTERFACE_INFO="xilinx.com:signal:reset:1.0 pixel_reset RST" *) output wire pixel_reset,
 output wire window_valid,
 output wire [23:0] capture_rgb,output wire capture_de,capture_vs,capture_mask,
 output wire [15:0] out_x,out_y,output reg [31:0] config_active=0,
 output wire [831:0] regions_ref,
 output wire [511:0] capture_region_boxes,output wire [255:0] capture_region_areas,
 output wire [31:0] capture_region_seq,capture_region_status,
 output wire [31:0] candidate_count_ref,bbox_min_ref,bbox_max_ref,snapshot_seq_ref,snapshot_config_ref,snapshot_status_ref,
 output wire [31:0] brightness_count_ref,brightness_sum_ref,brightness_seq_ref,brightness_config_ref,brightness_min_ref,brightness_max_ref,mask_crc_ref);
 wire [23:0] original,core_original;wire [7:0] gray,edgep,smooth,core_gray,core_edge,core_smooth;wire de,hs,vs,core_de,core_hs,core_vs;
 video_core #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.H_TOTAL(H_TOTAL)) core(
 .pixel_clk(pixel_clk),.control_clk(control_clk),.reset(reset),.mode_request(2'b0),
 .rgb_in(rgb_in),.de_in(de_in),.hs_in(hs_in),.vs_in(vs_in),
 .rgb_out(core_original),.de_out(core_de),.hs_out(core_hs),.vs_out(core_vs),
 .frame_count(),.frame_pixels(),.frame_lines(),.line_pixels(),.format_ok(),.mode_active(),
 .pixel_reset(pixel_reset),.window_valid(),.gray_out(core_gray),.edge_out(core_edge),.smooth_out(core_smooth));
 wire [7:0] valley_score,valley_wide_score;
 dual_scale_valley #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.H_TOTAL(H_TOTAL)) valley(
 .clk(pixel_clk),.reset(pixel_reset),.gray(core_gray),.rgb(core_original),.de(core_de),.hs(core_hs),.vs(core_vs),
 .rgb_out(original),.de_out(de),.hs_out(hs),.vs_out(vs),.score(valley_score),.score_wide(valley_wide_score));
 raster_delay #(.WIDTH(24),.WORDS(16*H_TOTAL+18)) aux_delay(
 .clk(pixel_clk),.reset(pixel_reset),.din({core_gray,core_edge,core_smooth}),.dout({gray,edgep,smooth}));
 wire [95:0] cfg;
 config_bridge bridge(control_clk,pixel_clk,config_request,roi_min_request,roi_max_request,cfg);
 reg [31:0] roi_min=0,roi_max=0;reg pvs=0,pde=0;reg [15:0] x=0,y=0;
 always @(posedge pixel_clk)begin
  if(pixel_reset)begin config_active<=0;roi_min<=0;roi_max<=0;pvs<=0;pde<=0;x<=0;y<=0;end
  else begin
   pvs<=vs;pde<=de;
   if(vs && !pvs)begin config_active<=cfg[31:0];roi_min<=cfg[63:32];roi_max<=cfg[95:64];x<=0;y<=0;end
   else begin if(de)x<=x+1'b1;else x<=0;if(pde && !de)y<=y+1'b1;end
  end
 end
 wire roi_ok=!config_active[20] || (x>=roi_min[15:0] && x<=roi_max[15:0] && y>=roi_min[31:16] && y<=roi_max[31:16]);
 // Tile source 3: local dark contrast, computed entirely in PL.
 // Gaussian weights sum to 16. Smooth and gray are center-aligned by video_core.
 wire [7:0] dark_contrast=config_active[23]?valley_score:((smooth>gray)?smooth-gray:8'd0);
 wire [7:0] intensity=config_active[17:16]==3?dark_contrast:config_active[17:16]==1?smooth:config_active[17:16]==2?edgep:gray;
 brightness_stats #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) brightness(
 .clk(pixel_clk),.control_clk(control_clk),.reset(pixel_reset),.de(de),.vs(vs),.gray(gray),.include_pixel(roi_ok),
 .config_word(config_active),.roi_min(roi_min),.roi_max(roi_max),
 .count_ref(brightness_count_ref),.sum_ref(brightness_sum_ref),.seq_ref(brightness_seq_ref),
 .config_ref(brightness_config_ref),.min_ref(brightness_min_ref),.max_ref(brightness_max_ref));
 // bit19 selects strict dark (<T) versus strict bright (>T) candidates.
 wire mask=de && roi_ok && ((config_active[19] && config_active[17:16]!=3) ? intensity<config_active[15:8] : intensity>config_active[15:8]);
 // V1.6 bit24 enables weak-crack support. Ceil(T/2) avoids 8-bit overflow.
 wire grow_enable=config_active[24] && config_active[23] && config_active[17:16]==3;
 wire [7:0] low_threshold={1'b0,config_active[15:9]}+{7'b0,config_active[8]};
 // bit27 opts into wider weak support. Strong seeds, thresholds and stage
 // count are unchanged. Clearing it reproduces the original mask algorithm.
 wire [7:0] weak_intensity=(grow_enable && config_active[27] && valley_wide_score>intensity)?valley_wide_score:intensity;
 wire weak_mask=de && roi_ok && weak_intensity>low_threshold;
 wire [23:0] preview=config_active[2:0]==1?{3{gray}}:config_active[2:0]==2?{3{edgep}}:config_active[2:0]==3?{3{smooth}}:original;
 // bit18: 0 opening (AND then OR), 1 closing (OR then AND).
 wire m1,d1,h1,v1,w1,w2;wire [52:0] side1;
 raster_morph #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.H_TOTAL(H_TOTAL),.SIDE_WIDTH(53)) pass1(
 pixel_clk,pixel_reset,config_active[18],mask,de,hs,vs,{original,config_active[2:0],roi_ok,mask,preview},m1,d1,h1,v1,side1,grow_enable,weak_mask,w1);
 wire m2,d2,h2,v2;wire [53:0] side2;
 raster_morph #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.H_TOTAL(H_TOTAL),.SIDE_WIDTH(54)) pass2(
 pixel_clk,pixel_reset,!config_active[18],m1,d1,h1,v1,{side1[52:29],m1,side1[28:0]},m2,d2,h2,v2,side2,grow_enable,w1,w2);
 // V1.24 bit25 adds two bounded support stages. With bit25 clear they
 // copy each center bit, retaining the original two-stage mask at equal latency.
 wire extra_grow=grow_enable && config_active[25];
 wire m3,w3,d3,h3,v3,m_final,w_final,d_final,h_final,v_final;
 wire [53:0] side3,side_final;
 raster_morph #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.H_TOTAL(H_TOTAL),.SIDE_WIDTH(54),.BYPASS_WHEN_NOT_GROW(1)) pass3(
 pixel_clk,pixel_reset,1'b0,m2,d2,h2,v2,side2,m3,d3,h3,v3,side3,extra_grow,w2,w3);
 raster_morph #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.H_TOTAL(H_TOTAL),.SIDE_WIDTH(54),.BYPASS_WHEN_NOT_GROW(1)) pass4(
 pixel_clk,pixel_reset,1'b0,m3,d3,h3,v3,side3,m_final,d_final,h_final,v_final,side_final,extra_grow,w3,w_final);
 // bit22 bypasses erosion/dilation while retaining identical raster latency.
 // The raw candidate is carried alongside the original pixels in side_final[24].
 wire final_mask=(grow_enable?m_final:(config_active[22]?side_final[24]:m_final)) && side_final[25];
 assign capture_rgb=side_final[53:30];assign capture_de=d_final;assign capture_vs=v_final;assign capture_mask=final_mask;
 wire [2:0] shown_mode=side_final[28:26];
 wire [23:0] shown=shown_mode==4?{24{side_final[24]}}:
  shown_mode==5?{24{side_final[29] && side_final[25]}}:
  shown_mode==6?{24{final_mask}}:
  shown_mode==7?((final_mask && !config_active[21])?24'hff0000:side_final[23:0]):side_final[23:0];
 candidate_stats #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) candidates(
 .clk(pixel_clk),.control_clk(control_clk),.reset(pixel_reset),.de(d_final),.vs(v_final),.mask(final_mask),.config_word(config_active),
 .count_ref(candidate_count_ref),.min_ref(bbox_min_ref),.max_ref(bbox_max_ref),.seq_ref(snapshot_seq_ref),.config_ref(snapshot_config_ref),.status_ref(snapshot_status_ref),.crc_ref(mask_crc_ref));
 wire [23:0] boxed;
 wire [511:0] region_boxes;wire [255:0] region_areas;wire [31:0] region_seq,region_status;
 assign capture_region_boxes=region_boxes;assign capture_region_areas=region_areas;
 assign capture_region_seq=region_seq;assign capture_region_status=region_status;
 region_grid #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) regions(
 .clk(pixel_clk),.control_clk(control_clk),.reset(pixel_reset),.de(d_final),.vs(v_final),.mask(final_mask),
 .boxes(region_boxes),.areas(region_areas),.result_seq(region_seq),.result_status(region_status),.snapshot_ref(regions_ref));
 reg [15:0] box_x=0,box_y=0;reg box_pd=0,box_pv=0;
 always @(posedge pixel_clk)begin
  if(pixel_reset)begin box_x<=0;box_y<=0;box_pd<=0;box_pv<=0;end
  else begin
   box_pd<=d_final;box_pv<=v_final;
   if(v_final && !box_pv)begin box_x<=0;box_y<=0;end
   else begin if(d_final)box_x<=box_x+1'b1;else box_x<=0;if(box_pd && !d_final)box_y<=box_y+1'b1;end
  end
 end
 reg box_edge;integer bi;
 reg [15:0] lx,ly,hx,hy;
 always @*begin
  box_edge=0;lx=0;ly=0;hx=0;hy=0;
  for(bi=0;bi<8;bi=bi+1)begin
   lx=region_boxes[bi*64+:16];ly=region_boxes[bi*64+16+:16];hx=region_boxes[bi*64+32+:16];hy=region_boxes[bi*64+48+:16];
   if(bi<region_status[3:0] && !region_status[31] && (((box_x==lx || box_x==hx) && box_y>=ly && box_y<=hy) || ((box_y==ly || box_y==hy) && box_x>=lx && box_x<=hx)))box_edge=1;
  end
 end
 assign boxed=(d_final && config_active[21] && shown_mode==7 && box_edge)?24'hff0000:shown;
 video_stats stats(pixel_clk,pixel_reset,boxed,d_final,h_final,v_final,rgb_out,de_out,hs_out,vs_out,
 frame_count,frame_pixels,frame_lines,line_pixels,format_ok);
 reg [15:0] ox=0,oy=0;reg od=0,ov=0;reg [2:0] mode_q=0;
 always @(posedge pixel_clk)begin
  if(pixel_reset)begin ox<=0;oy<=0;od<=0;ov<=0;mode_q<=0;end
  else begin
   od<=de_out;ov<=vs_out;mode_q<=shown_mode;
   if(vs_out && !ov)begin ox<=0;oy<=0;end
   else begin if(de_out)ox<=ox+1'b1;else ox<=0;if(od && !de_out)oy<=oy+1'b1;end
  end
 end
 assign out_x=ox;assign out_y=oy;assign mode_active=mode_q;
 assign window_valid=de_out && ox>0 && oy>0 && ox<WIDTH-1 && oy<HEIGHT-1;
endmodule
