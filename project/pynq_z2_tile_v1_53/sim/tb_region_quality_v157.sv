`timescale 1ns/1ps
module tb_region_quality_v157;
 localparam W=1280,H=720,HT=1650,FRAMES=65;
 reg clk=0,control_clk=0,reset=1,de=0,vs=0,mask=0,trusted=0,enabled=0;
 always #5 clk=~clk;always #4 control_clk=~control_clk;
 wire [511:0] boxes;wire [255:0] areas;wire [31:0] seq,status;wire [831:0] snap;
 region_quality_v157 dut(.clk(clk),.control_clk(control_clk),.reset(reset),.de(de),.vs(vs),.mask(mask),.trusted_mask(trusted),.quality_enable(enabled),.boxes(boxes),.areas(areas),.result_seq(seq),.result_status(status),.snapshot_ref(snap));
 reg [7:0] pixels[0:W*H-1];reg [31:0] expected[0:24];reg policy[0:FRAMES-1],flip[0:FRAMES-1];
 integer f,x,y,j,fd,got,proof;string root,path,result;
 task check_previous(input integer index);
 begin
  path=$sformatf("%s/%0d.hex",root,index);$readmemh(path,expected);
  if(dut.state!==0 || seq!==index+1 || status!==expected[0])$fatal(1,"frame %0d seq %0d status %h expected %h state %0d",index,seq,status,expected[0],dut.state);
  for(j=0;j<expected[0][3:0];j=j+1)begin
   if(boxes[j*64+:32]!==expected[1+j*3] || boxes[j*64+32+:32]!==expected[2+j*3] || areas[j*32+:32]!==expected[3+j*3])$fatal(1,"box mismatch frame %0d box %0d",index,j);
  end
  if(snap[31:0]!==seq || snap[63:32]!==status || snap[575:64]!==boxes || snap[831:576]!==areas)$fatal(1,"CDC mismatch");
  $display("PASS region frame %0d/%0d boxes=%0d",index+1,FRAMES,status[3:0]);
 end endtask
 initial begin
  if(!$value$plusargs("ROOT=%s",root) || !$value$plusargs("RESULT=%s",result))$fatal(1,"missing paths");
  $readmemh({root,"/policy.mem"},policy);$readmemh({root,"/flip.mem"},flip);
  repeat(10)@(negedge clk);reset=0;
  for(f=0;f<FRAMES;f=f+1)begin
   enabled=policy[f];vs=1;repeat(5*HT)@(negedge clk);vs=0;repeat(20*HT)@(negedge clk);
   if(f>0)check_previous(f-1);
   path=$sformatf("%s/%0d.bin",root,f);fd=$fopen(path,"rb");got=$fread(pixels,fd);$fclose(fd);if(got!=W*H)$fatal(1,"bad input %0d",got);
   for(y=0;y<H;y=y+1)begin
    for(x=0;x<W;x=x+1)begin
     @(negedge clk);de=1;mask=pixels[y*W+x][0];trusted=pixels[y*W+x][1];
     if(flip[f] && (y>0 || x>0))enabled=!policy[f];
    end
    @(negedge clk);de=0;mask=0;trusted=0;repeat(HT-W-1)@(negedge clk);
   end
   repeat(5*HT)@(negedge clk);
  end
  repeat(25*HT)@(negedge clk);check_previous(FRAMES-1);
  proof=$fopen(result,"w");$fdisplay(proof,"PASS %0d native720p frames, %0d pixels: exact boxes/areas/status/CDC, evidence boundaries, capacity, frame policy and 49500-clock blanking",FRAMES,FRAMES*W*H);$fclose(proof);$finish;
 end
 initial begin #2000000000;$fatal(1,"timeout");end
endmodule
