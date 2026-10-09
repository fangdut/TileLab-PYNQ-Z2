`timescale 1ns/1ps
// V1.41 fixed scheduling: real raster cadence, injected candidate mask.
// No detector, CPU, DMA, network, or physical HDMI claim is made by this test.
module tb_capture_region_porch_fixed;
 localparam W=1280,H=720,HT=1650,VT=750,TOP=25,PX=W*H,FRAMES=12;
 reg clk=0,control_clk=0,reset=1,de=0,vs=0,mask=0;
 always #6.734 clk=~clk;
 always #5 control_clk=~control_clk;
 reg [31:0] request=0;
 wire [511:0] boxes;wire [255:0] areas;wire [31:0] rseq,rstatus;
 wire [831:0] snapshot;
 region_grid regions(.clk(clk),.control_clk(control_clk),.reset(reset),.de(de),.vs(vs),.mask(mask),
  .boxes(boxes),.areas(areas),.result_seq(rseq),.result_status(rstatus),.snapshot_ref(snapshot));
 wire [31:0] data;wire valid,last;
 frame_capture capture(.pixel_clk(clk),.control_clk(control_clk),.reset(reset),.request(request),
  .rgb(24'h5a5a5a),.de(de),.vs(vs),.mask(mask),.config_word(32'h00f32407),
  .region_boxes(boxes),.region_areas(areas),.region_seq(rseq),.region_status(rstatus),
  .m_axis_tdata(data),.m_axis_tvalid(valid),.m_axis_tready(1'b1),.m_axis_tlast(last),
  .cap_seq(),.cap_count(),.cap_min(),.cap_max(),.cap_status(),.cap_config());

 function automatic integer case_id(input integer seq);
  if(seq==2)case_id=1;
  else if(seq>=3 && seq<=6)case_id=2;
  else if(seq>=7 && seq<=10)case_id=3;
  else case_id=0;
 endfunction
 function automatic bit expected_mask(input integer seq,x,y);
  case(case_id(seq))
   1:expected_mask=x>=320 && x<352 && y>=320 && y<352;
   2:expected_mask=1;
   // Exactly 36*18 occupied cells, not claimed as an actual detector ROI.
   3:expected_mask=x>=64 && x<1216 && y>=64 && y<640;
   default:expected_mask=0;
  endcase
 endfunction
 function automatic integer expected_count(input integer seq);
  case(case_id(seq))
   1:expected_count=1024;
   2:expected_count=921600;
   3:expected_count=663552;
   default:expected_count=0;
  endcase
 endfunction
 // Byte-table reference is deliberately separate from production word XOR.
 reg [31:0] crc_table[0:255];
 function automatic [31:0] word_crc(input [31:0] old_crc,value);
  reg [31:0] c;integer b;
  begin
   c=old_crc;
   for(b=0;b<4;b=b+1)c=(c>>8)^crc_table[(c^(value>>(8*b)))&255];
   word_crc=c;
  end
 endfunction
 reg [31:0] trailer[0:39];
 function automatic [31:0] descriptor_crc;
  reg [31:0] c;integer j;
  begin
   c=32'hffffffff;
   for(j=0;j<40;j=j+1)c=word_crc(c,j==8?32'b0:trailer[j]);
   descriptor_crc=~c;
  end
 endfunction

 integer cycle=0,drive_frame=0,words=0,packets=0,invalid_packets=0,packet_seq=0;
 integer region_results=0,last_rseq=0,previous_packet_seq=0;
 integer end_de[0:FRAMES+1],vs_cycle[0:FRAMES+1];
 integer packet_file,region_file,boundary_file,descriptor_file;
 reg old_vs=0,old_de=0;
 reg [31:0] pixel_crc=32'hffffffff,expected_word;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(!reset)begin
   if(vs && !old_vs)begin
    vs_cycle[drive_frame]=cycle;
    $fwrite(boundary_file,"%0d,%0d,%0d,%0d,%0d,%0d\n",drive_frame,case_id(drive_frame),cycle,capture.state,capture.seq,rseq);
   end
   if(old_de && !de && regions.y==H-1)end_de[drive_frame]=cycle;
   old_vs=vs;old_de=de;
   if(valid)begin
    if(words==0)begin packet_seq=capture.seq;pixel_crc=32'hffffffff;end
    if(words<PX)begin
     expected_word={7'b0,expected_mask(packet_seq,words%W,words/W),24'h5a5a5a};
     if(data!==expected_word)$fatal(1,"Pixel mismatch seq=%0d word=%0d actual=%h expected=%h",packet_seq,words,data,expected_word);
     pixel_crc=word_crc(pixel_crc,data);
    end else if(words<PX+40)trailer[words-PX]=data;
    else $fatal(1,"Packet too long");
    words=words+1;
    if(last)begin
     if(words!=PX+40)$fatal(1,"Packet words=%0d",words);
     if(trailer[0]!==32'h54465337 || trailer[2]!==packet_seq || packet_seq<=previous_packet_seq)$fatal(1,"Packet identity");
     if(trailer[1]!==~pixel_crc || trailer[8]!==descriptor_crc())$fatal(1,"CRC mismatch seq=%0d",packet_seq);
     if(trailer[3]!==expected_count(packet_seq) || trailer[35]!==PX*4)$fatal(1,"Packet counts");
     if(trailer[6][31] || trailer[9][31] || packet_seq!=previous_packet_seq+1)$fatal(1,"Fixed capture lost or invalidated seq=%0d",packet_seq);
     for(integer j=0;j<40;j=j+1)$fwrite(descriptor_file,"%0d,%0d,%08x\n",packet_seq,j,trailer[j]);
     $fwrite(packet_file,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%08x,%08x,%08x,%08x,%0d,%0d\n",
      packet_seq,case_id(packet_seq),cycle,words,words*4,trailer[6][31],trailer[9][31],trailer[1],~pixel_crc,trailer[8],descriptor_crc(),trailer[3],packet_seq-previous_packet_seq-1);
     $display("PACKET seq=%0d case=%0d words=%0d invalid=%0d/%0d pixel_crc=PASS descriptor_crc=PASS",packet_seq,case_id(packet_seq),words,trailer[6][31],trailer[9][31]);
     if(trailer[6][31])invalid_packets=invalid_packets+1;
     packets=packets+1;previous_packet_seq=packet_seq;words=0;
    end
   end
  end
  #1;
  if(!reset && rseq!=last_rseq)begin
   if(rstatus[31] || rseq>FRAMES)$fatal(1,"Region processing was invalid");
   if((case_id(rseq)==0 && rstatus!=0) || (case_id(rseq)!=0 && (rstatus!=1 || areas[31:0]!=expected_count(rseq))))$fatal(1,"Region result mismatch seq=%0d status=%h area=%d",rseq,rstatus,areas[31:0]);
   $fwrite(region_file,"%0d,%0d,%0d,%0d,%0d,%0d,%08x,%0d\n",rseq,case_id(rseq),end_de[rseq],cycle,cycle-end_de[rseq],vs_cycle[rseq]+HT*VT, rstatus,areas[31:0]);
   $display("REGION seq=%0d case=%0d latency=%0d next_vs_delta=%0d status=%h",rseq,case_id(rseq),cycle-end_de[rseq],vs_cycle[rseq]+HT*VT-end_de[rseq],rstatus);
   region_results=region_results+1;last_rseq=rseq;
  end
 end

 integer x,y,f,j,b;reg [31:0] c;
 initial begin
  for(j=0;j<256;j=j+1)begin
   c=j;for(b=0;b<8;b=b+1)c=c[0]?(c>>1)^32'hedb88320:c>>1;
   crc_table[j]=c;
  end
  for(j=0;j<=FRAMES+1;j=j+1)begin end_de[j]=0;vs_cycle[j]=0;end
  packet_file=$fopen("packets.csv","w");region_file=$fopen("regions.csv","w");
  boundary_file=$fopen("boundaries.csv","w");descriptor_file=$fopen("descriptors.csv","w");
  $fwrite(packet_file,"seq,case_id,tlast_cycle,words,bytes,capture_bad,region_bad,pixel_crc,reference_pixel_crc,descriptor_crc,reference_descriptor_crc,candidate_count,skipped_input_frames\n");
  $fwrite(region_file,"seq,case_id,last_de_fall_cycle,published_cycle,latency_cycles,next_vs_cycle,status,area\n");
  $fwrite(boundary_file,"seq,case_id,vs_cycle,capture_state_before,capture_seq_before,region_seq_before\n");
  $fwrite(descriptor_file,"seq,index,word\n");
  repeat(8)@(negedge clk);reset=0;request=2;repeat(12)@(negedge clk);
  for(f=1;f<=FRAMES;f=f+1)begin
   for(y=0;y<VT;y=y+1)for(x=0;x<HT;x=x+1)begin
    @(negedge clk);drive_frame=f;vs=y<5;de=y>=TOP && y<TOP+H && x<W;
    mask=de && expected_mask(f,x,y-TOP);
   end
  end
  // Only finish already-sent metadata; no extra stimulus frame is armed.
  @(negedge clk);de=0;vs=0;mask=0;repeat(200)@(negedge clk);
  if(words!=0 || packets!=FRAMES || invalid_packets!=0 || region_results!=FRAMES)$fatal(1,"Unexpected fixed totals packets=%0d bad=%0d regions=%0d words=%0d",packets,invalid_packets,region_results,words);
  $fclose(packet_file);$fclose(region_file);$fclose(boundary_file);$fclose(descriptor_file);
  $display("PASS V141 PORCH FIXED: 12 region frames, 12 full CRC-correct packets, no invalid or skipped frames");
  $finish;
 end
 initial begin #300000000;$fatal(1,"Simulation timeout");end
endmodule
