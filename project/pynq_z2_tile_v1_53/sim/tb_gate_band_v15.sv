`timescale 1ns/1ps
module tb_gate_band_v15;
 reg clk=0,control=0,reset=1;always #5 clk=~clk;always #7 control=~control;
 reg [31:0] rs=0,status=0;reg de=0,vs=0,mask=0;reg [23:0] rgb=0;
 frame_capture #(.WIDTH(256),.HEIGHT(720)) dut(.pixel_clk(clk),.control_clk(control),.reset(reset),.request(32'd2),.rgb(rgb),.de(de),.vs(vs),.mask(mask),.config_word(32'h00f32407),.region_boxes(512'd0),.region_areas(256'd0),.region_seq(rs),.region_status(status),.m_axis_tdata(),.m_axis_tvalid(),.m_axis_tready(1'b1),.m_axis_tlast(),.cap_seq(),.cap_count(),.cap_min(),.cap_max(),.cap_status(),.cap_config());
 integer x,y;
 task frame(input integer id,input bit tile,input bit stripe,input integer expect_gate,input integer expect_flags);
 begin
  @(negedge clk);vs=1;repeat(4)@(negedge clk);vs=0;repeat(6)@(negedge clk);
  for(y=0;y<720;y=y+1)begin
   for(x=0;x<256;x=x+1)begin
    de=1;mask=tile && stripe && x>=112 && x<144 && y>=110 && y<610;
    rgb=tile && !mask?24'hc0c0c0:24'h202020;@(negedge clk);
   end
   de=0;mask=0;repeat(16)@(negedge clk);
  end
  rs=id;status=stripe?1:0;repeat(200)@(negedge clk);
  if(dut.gate_count!=expect_gate)$fatal(1,"Band count %d expected %d",dut.gate_count,expect_gate);
  if(dut.product_id!=1)$fatal(1,"Physical tile identity split at frame %d",id);
  if((dut.product_flags&5)!=expect_flags)$fatal(1,"Presence/end flags at %d: %h",id,dut.product_flags);
 end endtask
 initial begin
  repeat(12)@(negedge clk);reset=0;repeat(12)@(negedge clk);
  frame(1,1,0,32000,1);
  // The old center column sees zero bright pixels for two consecutive frames.
  // The new band still sees 16000 and must retain the same product identity.
  frame(2,1,1,16000,1);frame(3,1,1,16000,1);frame(4,1,0,32000,1);
  frame(5,0,0,0,0);frame(6,0,0,0,4);
  $display("PASS 64-column gate keeps one product across a 32-pixel full-height dark stripe and ends after two empty frames");$finish;
 end
 initial begin #30000000;$fatal(1,"Gate band simulation timeout");end
endmodule
