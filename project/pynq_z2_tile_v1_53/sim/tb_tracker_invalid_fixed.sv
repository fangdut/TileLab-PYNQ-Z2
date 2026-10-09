`timescale 1ns/1ps
// Explicit lifecycle/ranking oracles, not an implementation-equivalence test.
module tb_tracker_invalid_fixed;
 reg clk=0,reset=1,valid=0;always #5 clk=~clk;
 reg [15:0] gate=0,lo=100,hi=1170;reg [31:0] area=500,status=0;
 wire done;wire [31:0] id,flags,score;
 product_tracker #(.MIN_GATE(12800)) dut(.clk(clk),.reset(reset),.frame_valid(valid),.gate_pixels(gate),.surface_xmin(lo),.surface_xmax(hi),.candidate_count(area),.region_status(status),.decision_valid(done),.product_id(id),.flags(flags),.score(score));
 integer fd,n=0,invalid_count=0,starts=0,ends=0,updates=0;reg [31:0] saved_score;
 reg [84:0] saved_state;
 task observe(input integer g,input reg [31:0] s,input integer a,l,h,expected_id,expected_flags);
 begin @(negedge clk);gate=g;status=s;area=a;lo=l;hi=h;
  saved_state={dut.live,dut.quiet,dut.serial,dut.best_area,dut.best_distance,dut.best_complete};saved_score=score;valid=1;
  @(negedge clk);valid=0;n=n+1;
  if(!done || id!=expected_id || flags!=expected_flags)$fatal(1,"obs%0d id=%0d flags=%x done=%b",n,id,flags,done);
  if(s[31])begin
   invalid_count=invalid_count+1;
   if({dut.live,dut.quiet,dut.serial,dut.best_area,dut.best_distance,dut.best_complete}!==saved_state || score!==saved_score)$fatal(1,"invalid observation changed retained state obs%0d",n);
  end
  if(flags&2)starts=starts+1;if(flags&4)ends=ends+1;if(flags&8)updates=updates+1;
  $fwrite(fd,"%0d,%0d,%08x,%0d,%08x,%0d,%0d,%0d\n",n,g,s,id,flags,dut.live,dut.quiet,dut.best_area);
  @(negedge clk);if(done)$fatal(1,"decision must be one pulse");
 end endtask
 initial begin
  fd=$fopen("observations.csv","w");$fwrite(fd,"observation,gate,region_status,product_id,flags,live,quiet,best_area\n");
  repeat(4)@(negedge clk);reset=0;
  observe(16000,32'h80000001,900,0,1279,0,0); // Invalid bright input cannot start ID1.
  observe(16000,1,500,100,1170,1,27);
  observe(0,32'h80000001,0,0,0,1,0);
  observe(0,32'h80000001,0,0,0,1,0);
  observe(16000,1,500,100,1170,1,17); // Same tile, same best, no new start/update.
  observe(32000,32'h80000001,99999,200,1079,1,0); // Invalid centered high area cannot win.
  observe(16000,1,500,100,1170,1,17);
  observe(16000,1,600,100,1170,1,25); // Valid tie-center larger area still wins.
  observe(16000,1,100,200,1079,1,25); // Valid more-centered image outranks area.
  observe(0,0,0,0,0,1,0); // First valid clear observation.
  observe(16000,32'h80000001,999,80,1199,1,0); // Invalid presence cannot reset quiet.
  observe(0,0,0,0,0,1,4); // Second valid clear ends only once.
  observe(16000,32'h80000001,900,100,1170,0,0); // Invalid idle must not allocate.
  observe(12800,1,500,100,1170,2,27); // Inclusive gate and sequential ID2.
  observe(0,0,0,0,0,2,0);
  observe(16000,1,500,100,1170,2,17); // Valid presence resets one-clear debounce.
  observe(0,0,0,0,0,2,0);
  observe(0,0,0,0,0,2,4);
  reset=1;repeat(2)@(negedge clk);reset=0;
  observe(16000,32'h80000001,500,100,1170,0,0);
  observe(16000,1,500,100,1170,3,27); // Video reset never reuses a valid ID.
  if(n!=20||invalid_count!=7||starts!=3||ends!=2||updates!=5)$fatal(1,"coverage n=%0d invalid=%0d starts=%0d ends=%0d updates=%0d",n,invalid_count,starts,ends,updates);
  $fclose(fd);$display("PASS V142 FIXED:20 decisions,7 invalid frozen,3 starts,2 ends,5 best updates");$finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
