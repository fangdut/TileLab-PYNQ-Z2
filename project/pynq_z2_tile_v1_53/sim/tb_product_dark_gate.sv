`timescale 1ns/1ps
// V1.37 baseline experiment: current production capture + product tracker.
// Synthetic RGB raster, injected qualified mask/regions. This is NOT an image
// detector test, HDMI timing simulation, firmware test, or board observation.
module tb_product_dark_gate;
 localparam W=1280,H=720,PIXELS=W*H;
 reg clk=0,control=0,reset=1;
 always #5 clk=~clk;
 always #7 control=~control;
 reg [31:0] request=0,config_word=32'h00f32407,region_seq=0,region_status=1;
 reg [511:0] region_boxes=0;reg [255:0] region_areas=1200;
 reg [23:0] rgb=0;reg de=0,vs=0,mask=0;
 wire [31:0] data;wire valid,last;
 frame_capture #(.WIDTH(W),.HEIGHT(H)) dut(
 .pixel_clk(clk),.control_clk(control),.reset(reset),.request(request),
 .rgb(rgb),.de(de),.vs(vs),.mask(mask),.config_word(config_word),
 .region_boxes(region_boxes),.region_areas(region_areas),
 .region_seq(region_seq),.region_status(region_status),
 .m_axis_tdata(data),.m_axis_tvalid(valid),.m_axis_tready(1'b1),.m_axis_tlast(last),
 .cap_seq(),.cap_count(),.cap_min(),.cap_max(),.cap_status(),.cap_config());
 reg [31:0] trailer[0:39];
 integer words=0,packets=0,expected_id=0,expected_flags=0,frame_seq=0;
 integer starts=0,ends=0,updates=0,fd,phase,index;
 always @(posedge clk)begin
  if(!reset && valid)begin
   if(words>=PIXELS && words<PIXELS+40)trailer[words-PIXELS]=data;
   words=words+1;
   if(last)begin
    if(words!=PIXELS+40)$fatal(1,"Packet size %0d",words);
    if(trailer[0]!==32'h54465336 || trailer[2]!==frame_seq)$fatal(1,"Invalid packet identity");
    if(trailer[3]!==1200 || trailer[9]!==1 || trailer[6][31])$fatal(1,"Injected alarm invalid/count wrong");
    if(trailer[37]!==expected_id || trailer[38]!==expected_flags)
     $fatal(1,"phase=%0d frame=%0d id/flags=%0d/%0d wanted=%0d/%0d",phase,index,trailer[37],trailer[38],expected_id,expected_flags);
    if(trailer[38]&2)starts=starts+1;
    if(trailer[38]&4)ends=ends+1;
    if(trailer[38]&8)updates=updates+1;
    packets=packets+1;words=0;
   end
  end
 end
 task frame(input integer gray_value,left,product,flags,expected_gate);
  integer x,y,value,old_packets;reg is_tile,is_crack;
  begin
   frame_seq=frame_seq+1;expected_id=product;expected_flags=flags;old_packets=packets;
   region_boxes=0;
   region_boxes[63:0]={16'd459,16'(left+105),16'd260,16'(left+100)};
   @(negedge clk);vs=1;de=0;repeat(4)@(negedge clk);vs=0;repeat(6)@(negedge clk);
   for(y=0;y<H;y=y+1)begin
    for(x=0;x<W;x=x+1)begin
     is_tile=x>=left && x<left+560 && y>=160 && y<560;
     is_crack=x>=left+100 && x<left+106 && y>=260 && y<460;
     // Both materials retain a 55-level crack contrast (90/35, 70/15).
     value=is_crack?gray_value-55:is_tile?gray_value:20;
     rgb={8'(value),8'(value),8'(value)};mask=is_crack;de=1;
     @(negedge clk);
    end
    de=0;mask=0;repeat(16)@(negedge clk);
   end
   region_seq=frame_seq;
   repeat(256)@(negedge clk);
   if(packets!=old_packets+1)$fatal(1,"Missing packet at frame_seq %0d",frame_seq);
   if(dut.gate_count!==expected_gate)$fatal(1,"Actual RTL gate=%0d wanted=%0d",dut.gate_count,expected_gate);
   $fwrite(fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\n",phase,index,frame_seq,left,gray_value,dut.gate_count,trailer[3],trailer[37],trailer[38],trailer[39]);
   $display("FRAME phase=%0d index=%0d gray=%0d left=%0d gate=%0d area=%0d id=%0d flags=%0d",phase,index,gray_value,left,dut.gate_count,trailer[3],trailer[37],trailer[38]);
  end
 endtask
 initial begin
  fd=$fopen("frames.csv","w");if(!fd)$fatal(1,"Cannot open frames.csv");
  $fwrite(fd,"case,case_frame,frame_id,tile_left,gray,gate_pixels,candidate_pixels,product_id,product_flags,selection_score\n");
  repeat(10)@(negedge clk);reset=0;request=2;repeat(16)@(negedge clk);
  phase=1;
  for(index=0;index<10;index=index+1)frame(70,80+index*80,0,0,0);
  if(starts!=0 || ends!=0 || updates!=0)$fatal(1,"Dark surface unexpectedly tracked");
  $display("EXPECTED_FAILURE dark_surface: qualified_region_frames=10 product_starts=0 product_ends=0 best_updates=0");
  phase=2;
  index=0;frame(90,80,1,27,12800);
  index=1;frame(90,160,1,25,25600);
  index=2;frame(90,240,1,25,25600);
  index=3;frame(70,320,1,0,0);
  index=4;frame(70,400,1,4,0);
  index=5;frame(90,480,2,27,25600);
  index=6;frame(90,560,2,17,24400);
  index=7;frame(90,640,2,17,12800);
  index=8;frame(90,720,2,0,0);
  index=9;frame(90,800,2,4,0);
  if(starts!=2 || ends!=2 || updates!=4 || packets!=20)$fatal(1,"Unexpected split totals");
  $display("EXPECTED_FAILURE two_frame_dip: physical_tile=1 product_starts=2 product_ends=2 best_updates=4");
  $display("PASS V137 baseline product gate experiment: both expected failures reproduced; module-level injected regions only");
  $fclose(fd);$finish;
 end
 initial begin #250000000;$fatal(1,"Simulation timeout");end
endmodule
