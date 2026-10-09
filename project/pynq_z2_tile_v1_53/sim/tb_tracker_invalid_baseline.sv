`timescale 1ns/1ps
// Negative reproduction: one unchanged physical tile, two invalid observations.
module tb_tracker_invalid_baseline;
 reg clk=0,reset=1,valid=0;always #5 clk=~clk;
 reg [15:0] gate=0;reg [31:0] status=0;wire done;wire [31:0] id,flags,score;
 product_tracker #(.MIN_GATE(12800)) dut(.clk(clk),.reset(reset),.frame_valid(valid),.gate_pixels(gate),.surface_xmin(16'd100),.surface_xmax(16'd1170),.candidate_count(32'd500),.region_status(status),.decision_valid(done),.product_id(id),.flags(flags),.score(score));
 integer fd,n=0;reg [31:0] first_id;
 task observe(input integer g,input reg [31:0] s);
 begin @(negedge clk);gate=g;status=s;valid=1;@(negedge clk);valid=0;
  if(!done)$fatal(1,"capture decision handshake did not complete");
  n=n+1;$fwrite(fd,"%0d,%0d,%08x,%0d,%08x,%0d,%0d\n",n,g,s,id,flags,dut.live,dut.quiet);
  @(negedge clk);if(done)$fatal(1,"decision_valid not a pulse");
 end endtask
 initial begin
  fd=$fopen("observations.csv","w");$fwrite(fd,"observation,gate,region_status,product_id,flags,live,quiet\n");
  repeat(4)@(negedge clk);reset=0;
  observe(16000,1);first_id=id;if(first_id!=1||!(flags&2))$fatal(1,"initial product start");
  observe(0,32'h80000001);if(dut.quiet!=1)$fatal(1,"expected baseline invalid observation to count as clear");
  observe(0,32'h80000001);if(!(flags&4)||dut.live)$fatal(1,"expected baseline false end");
  observe(16000,1);if(id!=first_id+1||!(flags&2))$fatal(1,"expected baseline same-tile ID split");
  // Video reset preserves serial. Invalid bright observation alone also starts an ID.
  reset=1;repeat(2)@(negedge clk);reset=0;
  observe(16000,32'h80000001);if(id!=3||!(flags&2)||!dut.live)$fatal(1,"expected baseline invalid false start");
  $fclose(fd);$display("PASS V142 NEGATIVE: invalid observations split one tile into IDs1/2 and false-start ID3; all5 decisions complete");$finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
