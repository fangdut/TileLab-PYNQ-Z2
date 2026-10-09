`timescale 1ns/1ps
module tb_capture_random_equivalence;
 reg clk=0,control=0,reset=1;always #5 clk=~clk;always #7 control=~control;
 reg [31:0] request=0,cfg=0,seq=0,status=0,rng=32'hcafe1547;
 reg [511:0] boxes=0;reg [255:0] areas=0;
 reg [23:0] rgb=0;reg de=0,vs=0,mask=0,ready=1;
 wire [31:0] data,golden_data;wire valid,last,golden_valid,golden_last;
 wire [191:0] caps,golden_caps;
 frame_capture #(.WIDTH(256),.HEIGHT(240)) dut(
 .pixel_clk(clk),.control_clk(control),.reset(reset),.request(request),.rgb(rgb),.de(de),.vs(vs),.mask(mask),.config_word(cfg),
 .region_boxes(boxes),.region_areas(areas),.region_seq(seq),.region_status(status),
 .m_axis_tdata(data),.m_axis_tvalid(valid),.m_axis_tready(ready),.m_axis_tlast(last),
 .cap_seq(caps[31:0]),.cap_count(caps[63:32]),.cap_min(caps[95:64]),.cap_max(caps[127:96]),.cap_status(caps[159:128]),.cap_config(caps[191:160]));
 frame_capture_v114 #(.WIDTH(256),.HEIGHT(240)) golden(
 .pixel_clk(clk),.control_clk(control),.reset(reset),.request(request),.rgb(rgb),.de(de),.vs(vs),.mask(mask),.config_word(cfg),
 .region_boxes(boxes),.region_areas(areas),.region_seq(seq),.region_status(status),
 .m_axis_tdata(golden_data),.m_axis_tvalid(golden_valid),.m_axis_tready(ready),.m_axis_tlast(golden_last),
 .cap_seq(golden_caps[31:0]),.cap_count(golden_caps[63:32]),.cap_min(golden_caps[95:64]),.cap_max(golden_caps[127:96]),.cap_status(golden_caps[159:128]),.cap_config(golden_caps[191:160]));
 task random_step;
 begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);end
 endtask
 integer cycles=0,packets=0,stalls=0,pixel_resets=0,crc_resets=0,trailer_resets=0,disabled=0;
 integer states[0:5];integer i,j,n,k;reg injected;
 always @(posedge clk)begin
  if(!reset && valid && ready && last)packets=packets+1;
  #1;
  if(!reset)begin
   cycles=cycles+1;states[dut.state]=states[dut.state]+1;
   if(valid && !ready)stalls=stalls+1;
   if(valid!==golden_valid || last!==golden_last || (valid && data!==golden_data) || caps!==golden_caps)
    $fatal(1,"Random observable mismatch cycle=%0d state=%0d",cycles,dut.state);
  end
 end
 task frame(input integer number);
 begin
  request=number%8==7?0:2;if(request==0)disabled=disabled+1;
  // V1.37 ABI-retargeted legacy reference covers only default presence mode.
  // Explicit low gate is validated separately by tb_product_low_gate.
  random_step();cfg=rng & ~32'h04000000;repeat(30)@(negedge clk);
  vs=1;repeat(4)@(negedge clk);vs=0;repeat(6)@(negedge clk);
  for(j=0;j<240;j=j+1)begin
   for(i=0;i<256;i=i+1)begin
    random_step();rgb=rng[23:0];mask=rng[29];ready=(rng[7:0]>8);de=1;
    if(number%6==1 && j==120 && i==128 && dut.state==1)begin
     reset=1;de=0;pixel_resets=pixel_resets+1;repeat(4)@(negedge clk);reset=0;
    end
    @(negedge clk);
   end
   de=0;mask=0;ready=1;repeat(16)@(negedge clk);
  end
  seq=dut.frame_id;random_step();status=rng;
  for(k=0;k<16;k=k+1)begin random_step();boxes[k*32+:32]=rng;end
  for(k=0;k<8;k=k+1)begin random_step();areas[k*32+:32]=rng;end
  injected=0;
  for(k=0;k<400;k=k+1)begin
   random_step();ready=(rng[3:0]>4);
   if(!injected && ((number%6==2 && dut.state==5 && dut.trailer_index==17) || (number%6==3 && dut.state==4 && dut.trailer_index==17)))begin
    if(dut.state==5)crc_resets=crc_resets+1;else trailer_resets=trailer_resets+1;
    injected=1;reset=1;repeat(4)@(negedge clk);reset=0;
   end
   @(negedge clk);
  end
  ready=1;repeat(100)@(negedge clk);
 end
 endtask
 initial begin
  for(n=0;n<6;n=n+1)states[n]=0;
  repeat(10)@(negedge clk);reset=0;
  for(n=0;n<24;n=n+1)frame(n);
  if(cycles<1500000 || packets<4 || stalls<1000 || pixel_resets<2 || crc_resets<2 || trailer_resets<2 || disabled!=3)$fatal(1,"Insufficient stress coverage");
  for(n=0;n<6;n=n+1)if(states[n]==0)$fatal(1,"Unvisited capture state");
  $display("RANDOM_EQ cycles=%0d packets=%0d stalls=%0d pixel_resets=%0d crc_resets=%0d trailer_resets=%0d disabled=%0d",cycles,packets,stalls,pixel_resets,crc_resets,trailer_resets,disabled);
  $display("PASS randomized V1.15/V1.14 cycle equivalence, metadata, enable, pixel/CRC/trailer resets and stalls");$finish;
 end
 initial begin #40000000;$fatal(1,"Random equivalence timeout");end
endmodule
