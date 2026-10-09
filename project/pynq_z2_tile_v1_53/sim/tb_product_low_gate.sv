`timescale 1ns/1ps
// Synthetic raster + injected valid mask/regions. Module validation only;
// not detector accuracy, physical HDMI timing, firmware, or board testing.
module tb_product_low_gate;
 localparam W=1280,H=720,PIXELS=W*H;
 localparam DEFAULT_CFG=32'h00f32407,LOW_CFG=32'h04f32407;
 reg clk=0,control=0,reset=1;
 always #5 clk=~clk;always #7 control=~control;
 reg [31:0] request=0,config_word=DEFAULT_CFG,region_seq=0,region_status=1;
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
 reg [31:0] trailer[0:39],expected_cfg=0;
 integer words=0,packets=0,expected_id=0,expected_flags=0,frame_seq=0;
 integer starts=0,ends=0,updates=0,crc_checks=0,fd,phase,index;
 // Independent byte-wise IEEE CRC-32 for the 40-word descriptor.
 function [31:0] descriptor_crc;
  integer word_index,byte_index,bit_index;reg [31:0] crc,value;
  begin
   crc=32'hffffffff;
   for(word_index=0;word_index<40;word_index=word_index+1)begin
    value=word_index==8?32'b0:trailer[word_index];
    for(byte_index=0;byte_index<4;byte_index=byte_index+1)begin
     crc=crc^((value>>(byte_index*8))&32'hff);
     for(bit_index=0;bit_index<8;bit_index=bit_index+1)
      crc=crc[0]?(crc>>1)^32'hedb88320:crc>>1;
    end
   end
   descriptor_crc=~crc;
  end
 endfunction
 always @(posedge clk)begin
  if(!reset && valid)begin
   if(words>=PIXELS && words<PIXELS+40)trailer[words-PIXELS]=data;
   words=words+1;
   if(last)begin
    if(words!=PIXELS+40)$fatal(1,"Packet size %0d",words);
    if(trailer[0]!==32'h54465337 || trailer[2]!==frame_seq)$fatal(1,"Invalid V137 packet identity");
    if(trailer[3]!==1200 || trailer[9]!==1 || trailer[6][31])$fatal(1,"Injected alarm invalid/count wrong");
    if(trailer[7]!==expected_cfg)$fatal(1,"Frame config changed expected=%08x actual=%08x",expected_cfg,trailer[7]);
    if(trailer[8]!==descriptor_crc())$fatal(1,"Descriptor CRC mismatch");
    if(trailer[37]!==expected_id || trailer[38]!==expected_flags)
     $fatal(1,"phase=%0d frame=%0d id/flags=%0d/%0d wanted=%0d/%0d",phase,index,trailer[37],trailer[38],expected_id,expected_flags);
    if(trailer[38]&2)starts=starts+1;
    if(trailer[38]&4)ends=ends+1;
    if(trailer[38]&8)updates=updates+1;
    crc_checks=crc_checks+1;packets=packets+1;words=0;
   end
  end
 end
 task frame(input [23:0] surface_rgb,input integer left,product,flags,expected_gate,input bit toggle_mid);
  integer x,y,crack_gray,old_packets;reg is_tile,is_crack;
  begin
   frame_seq=frame_seq+1;expected_id=product;expected_flags=flags;old_packets=packets;
   expected_cfg=config_word;
   region_boxes=0;region_boxes[63:0]={16'd459,16'(left+105),16'd260,16'(left+100)};
   crack_gray=surface_rgb[23:16]>=55?surface_rgb[23:16]-55:0;
   @(negedge clk);vs=1;de=0;repeat(4)@(negedge clk);vs=0;repeat(6)@(negedge clk);
   for(y=0;y<H;y=y+1)begin
    for(x=0;x<W;x=x+1)begin
     // Switch raw config after half the tile rows. Capture must retain the
     // first-pixel config, and the next frame must adopt the new setting.
     if(toggle_mid && y==360 && x==0)config_word=config_word^32'h04000000;
     is_tile=x>=left && x<left+560 && y>=160 && y<560;
     is_crack=x>=left+100 && x<left+106 && y>=260 && y<460;
     rgb=is_crack?{8'(crack_gray),8'(crack_gray),8'(crack_gray)}:is_tile?surface_rgb:24'h141414;
     mask=is_crack;de=1;@(negedge clk);
    end
    de=0;mask=0;repeat(16)@(negedge clk);
   end
   region_seq=frame_seq;repeat(256)@(negedge clk);
   if(packets!=old_packets+1)$fatal(1,"Missing packet at frame %0d",frame_seq);
   if(dut.gate_count!==expected_gate)$fatal(1,"Actual RTL gate=%0d wanted=%0d phase=%0d frame=%0d",dut.gate_count,expected_gate,phase,index);
   $fwrite(fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\n",phase,index,frame_seq,left,
    {2'b0,surface_rgb[23:16]}+{1'b0,surface_rgb[7:0],1'b0}+{2'b0,surface_rgb[15:8]},
    dut.gate_count,trailer[3],trailer[37],trailer[38],trailer[39],trailer[7],toggle_mid,trailer[0],trailer[8]);
   $display("FRAME phase=%0d index=%0d gate=%0d area=%0d id=%0d flags=%0d cfg=%08x crc=PASS",phase,index,dut.gate_count,trailer[3],trailer[37],trailer[38],trailer[7]);
  end
 endtask
 initial begin
  fd=$fopen("frames.csv","w");if(!fd)$fatal(1,"Cannot open frames.csv");
  $fwrite(fd,"case,case_frame,frame_id,tile_left,surface_luma,gate_pixels,candidate_pixels,product_id,product_flags,selection_score,config_word,toggled_midframe,magic,descriptor_crc\n");
  repeat(10)@(negedge clk);reset=0;request=2;repeat(16)@(negedge clk);
  phase=1;config_word=DEFAULT_CFG;
  for(index=0;index<10;index=index+1)frame(24'h464646,80+index*80,0,0,0,0);
  if(starts!=0 || ends!=0 || updates!=0)$fatal(1,"Default dark behavior changed");
  $display("PASS DEFAULT_DARK_UNCHANGED starts=0 ends=0");
  phase=2;
  index=0;frame(24'h5a5a5a,80,1,27,12800,0);
  index=1;frame(24'h5a5a5a,160,1,25,25600,0);
  index=2;frame(24'h5a5a5a,240,1,25,25600,0);
  index=3;frame(24'h464646,320,1,0,0,0);
  index=4;frame(24'h464646,400,1,4,0,0);
  index=5;frame(24'h5a5a5a,480,2,27,25600,0);
  index=6;frame(24'h5a5a5a,560,2,17,24400,0);
  index=7;frame(24'h5a5a5a,640,2,17,12800,0);
  index=8;frame(24'h5a5a5a,720,2,0,0,0);
  index=9;frame(24'h5a5a5a,800,2,4,0,0);
  if(starts!=2 || ends!=2 || updates!=4)$fatal(1,"Default dip behavior changed");
  $display("PASS DEFAULT_DIP_UNCHANGED starts=2 ends=2");
  phase=3;config_word=LOW_CFG;
  index=0;frame(24'h464646,80,3,27,12800,0);
  index=1;frame(24'h464646,160,3,25,25600,0);
  index=2;frame(24'h464646,240,3,25,25600,0);
  index=3;frame(24'h464646,320,3,25,25600,0);
  index=4;frame(24'h464646,400,3,17,25600,0);
  index=5;frame(24'h464646,480,3,17,25600,0);
  index=6;frame(24'h464646,560,3,17,24400,0);
  index=7;frame(24'h464646,640,3,17,12800,0);
  index=8;frame(24'h464646,720,3,0,0,0);
  index=9;frame(24'h464646,800,3,4,0,0);
  if(starts!=3 || ends!=3 || updates!=8)$fatal(1,"Low dark surface not one product");
  $display("PASS LOW_DARK_FIXED starts=1 ends=1");
  phase=4;
  index=0;frame(24'h5a5a5a,80,4,27,12800,0);
  index=1;frame(24'h5a5a5a,160,4,25,25600,0);
  index=2;frame(24'h5a5a5a,240,4,25,25600,0);
  index=3;frame(24'h464646,320,4,25,25600,0);
  index=4;frame(24'h464646,400,4,17,25600,0);
  index=5;frame(24'h5a5a5a,480,4,17,25600,0);
  index=6;frame(24'h5a5a5a,560,4,17,24400,0);
  index=7;frame(24'h5a5a5a,640,4,17,12800,0);
  index=8;frame(24'h5a5a5a,720,4,0,0,0);
  index=9;frame(24'h5a5a5a,800,4,4,0,0);
  if(starts!=4 || ends!=4 || updates!=12)$fatal(1,"Low dip surface not one product");
  $display("PASS LOW_DIP_FIXED starts=1 ends=1");
  phase=5;config_word=DEFAULT_CFG;
  index=0;frame(24'h272828,360,0,0,0,0); // L=159
  index=1;frame(24'h282828,360,0,0,0,0); // L=160
  index=2;frame(24'h4f5050,360,0,0,0,0); // L=319
  index=3;frame(24'h505050,360,5,27,25600,0); // L=320 inclusive
  index=4;frame(24'h141414,360,5,0,0,0);
  index=5;frame(24'h141414,360,5,4,0,0);
  config_word=LOW_CFG;
  index=6;frame(24'h272828,360,0,0,0,0); // L=159
  index=7;frame(24'h282828,360,6,27,25600,0); // L=160 inclusive
  index=8;frame(24'h4f5050,360,6,17,25600,0); // L=319
  index=9;frame(24'h505050,360,6,17,25600,0); // L=320
  index=10;frame(24'h141414,360,6,0,0,0);
  index=11;frame(24'h141414,360,6,4,0,0);
  $display("PASS LUMA_BOUNDARIES default=320_inclusive low=160_inclusive");
  phase=6;config_word=DEFAULT_CFG;
  index=0;frame(24'h464646,360,0,0,0,1); // Default frame ignores mid-frame low request.
  index=1;frame(24'h464646,360,7,27,25600,0); // The next frame adopts low.
  index=2;frame(24'h464646,360,7,17,25600,1); // Low frame ignores mid-frame default.
  index=3;frame(24'h464646,360,7,0,0,0); // Next frame adopts default; first gap.
  index=4;frame(24'h464646,360,7,4,0,0); // The unchanged two-frame policy ends it.
  if(starts!=7 || ends!=7 || updates!=15 || packets!=57 || crc_checks!=57)$fatal(1,"Validation totals mismatch");
  $display("PASS FRAME_CONFIG_LOCK descriptor_cfg_magic_crc_checks=57");
  $display("PASS V137 product low gate validation: default unchanged, dark/dip fixed, boundaries and frame config/descriptor CRC consistent");
  $fclose(fd);$finish;
 end
 initial begin #600000000;$fatal(1,"Simulation timeout");end
endmodule
