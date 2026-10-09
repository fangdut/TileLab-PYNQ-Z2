`timescale 1ns/1ps
module tb_frame_capture;
 localparam W=32,H=24,HT=44,VT=30;
 reg pc=0,cc=0;always #7 pc=~pc;always #2.5 cc=~cc;
 reg reset=1,de=0,vs=0,mask=0,ready=1;reg[31:0] request=0;reg[23:0] rgb=0;
 wire[31:0] data,seq,n,lo,hi,status,cfg;wire valid,last;
 frame_capture #(.WIDTH(W),.HEIGHT(H)) dut(pc,cc,reset,request,rgb,de,vs,mask,32'h80f31807,data,valid,ready,last,seq,n,lo,hi,status,cfg);
 integer count=0,errors=0,stage=0;integer xx,yy;reg[31:0] expected,held;reg stalled=0;
 always @(posedge pc)begin
  if(stalled && (data!==held || !valid))$fatal(1,"AXIS word changed under backpressure");
  stalled=valid&&!ready;held=data;
  if(valid&&ready)begin
   if(stage==1)begin
    xx=count%W;yy=count/W;
    expected=((xx==8||xx==9)?32'h01000000:0)|(xx<<16)|((xx^yy)<<8)|yy;
    if(data!==expected || last!==(count==W*H-1))begin $display("Capture mismatch %d %x %x",count,data,expected);errors=errors+1;end
   end
   count=count+1;
  end
 end
 task frame(input bit inject);
  integer x,y;
  begin
   for(y=0;y<VT;y=y+1)for(x=0;x<HT;x=x+1)begin
    @(negedge pc);vs=(y==0);de=(y>=3 && y<3+H && x<W);
    rgb={x[7:0],8'(y-3),8'(x^(y-3))};mask=(x==8||x==9);
    ready=!(inject && y==8 && x>=11 && x<=14);
   end
   @(negedge pc);de=0;vs=0;ready=1;repeat(100)@(negedge pc);
  end
 endtask
 initial begin
  repeat(20)@(negedge pc);reset=0;repeat(20)@(negedge pc);
  request=1;repeat(20)@(negedge pc);stage=1;frame(0);
  if(errors || count!=W*H || n!=48 || status!==32'hd || lo!==32'h00000008 || hi!==32'h00170009)$fatal(1,"Good frame rejected count=%d area=%d status=%x lo=%x hi=%x",count,n,status,lo,hi);
  $display("CAPTURE VALID PASS pixels=%d seq=%d",count,seq);
  request=0;repeat(20)@(negedge pc);stage=2;count=0;frame(1);
  if(!status[31] || status[0]!=0)$fatal(1,"Dropped pixels not marked invalid %x",status);
  $display("CAPTURE BACKPRESSURE PASS invalid_status=%x accepted_words=%d",status,count);
  $display("CAPTURE PASS");$finish;
 end
endmodule
