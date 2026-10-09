`timescale 1ns/1ps
module tb_region_full;
 reg clk=0,control_clk=0,reset=1,de=0,vs=0,mask=0;
 always #5 clk=~clk;always #4 control_clk=~control_clk;
 wire [511:0] boxes;wire [255:0] areas;wire [31:0] seq,status;wire [831:0] snap;
 region_grid #(.WIDTH(1280),.HEIGHT(720),.SHIFT(5)) dut(clk,control_clk,reset,de,vs,mask,boxes,areas,seq,status,snap);
 reg mem[0:921599];reg [31:0] expected[0:24];integer testno,x,y,j,k;string root,path;
 initial begin
  if(!$value$plusargs("ROOT=%s",root))$fatal(1,"ROOT missing");
  repeat(10)@(negedge clk);reset=0;
  for(testno=0;testno<3;testno=testno+1)begin
   path=$sformatf("%s/sim/region_full_vectors/%0d.hex",root,testno);$readmemh(path,mem);
   path=$sformatf("%s/sim/region_full_vectors/%0d_expected.hex",root,testno);$readmemh(path,expected);
   @(negedge clk);vs=1;repeat(4)@(negedge clk);vs=0;repeat(100)@(negedge clk);
   for(y=0;y<720;y=y+1)begin
    for(x=0;x<1280;x=x+1)begin @(negedge clk);de=1;mask=mem[y*1280+x];end
    @(negedge clk);de=0;mask=0;repeat(370)@(negedge clk);
   end
   // 20k clocks fit inside normal 720p vertical blanking (49.5k clocks
   // between last active pixel and next VS + back porch), including dense case.
   repeat(20000)@(negedge clk);
   if(seq!=testno+1 || status!==expected[0])$fatal(1,"case %0d seq=%d status=%h expected=%h state=%d",testno,seq,status,expected[0],dut.state);
   for(j=0;j<expected[0][3:0];j=j+1)begin
    if(boxes[j*64+:32]!==expected[1+j*3] || boxes[j*64+32+:32]!==expected[2+j*3] || areas[j*32+:32]!==expected[3+j*3])
     $fatal(1,"case %d box %d actual %h %h area %d expected %h %h %d",testno,j,boxes[j*64+:32],boxes[j*64+32+:32],areas[j*32+:32],expected[1+j*3],expected[2+j*3],expected[3+j*3]);
   end
   if(snap[31:0]!==seq || snap[63:32]!==status || snap[575:64]!==boxes || snap[831:576]!==areas)$fatal(1,"CDC mismatch");
   $display("REGION case %0d PASS boxes=%d overflow=%b",testno,status[3:0],status[8]);
  end
  $display("REGION PASS 2764800 exact pixels, eight-box overflow, dense graph, borders, noise and coherent CDC");$finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
