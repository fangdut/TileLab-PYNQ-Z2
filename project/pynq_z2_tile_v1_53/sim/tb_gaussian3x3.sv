`timescale 1ns/1ps
module tb_gaussian3x3;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,ce=1,iv=0,border=0;reg [71:0] win=0;
 wire ov;wire [7:0] pixel;
 gaussian3x3 dut(clk,reset,ce,iv,border,win,ov,pixel);
 integer a[0:8],weight[0:8],s,checks=0;reg [8:0] q[0:2],oldout;
 initial begin
  weight[0]=1;weight[1]=2;weight[2]=1;weight[3]=2;weight[4]=4;
  weight[5]=2;weight[6]=1;weight[7]=2;weight[8]=1;
  for(integer j=0;j<3;j++)q[j]=0;
  repeat(3) @(negedge clk);reset=0;
  for(integer n=0;n<16004;n++) begin
   @(negedge clk);oldout={ov,pixel};ce=(n<16 || n>=16000)?1:($urandom_range(0,3)!=0);
   iv=(n<16000) && ((n<16)||($urandom_range(0,4)!=0));border=(n%13==0);
   reset=(n==8000);s=0;
   for(integer j=0;j<9;j++) begin
    a[j]=$urandom_range(0,255);
    if(n==0)a[j]=0;
    if(n==1)a[j]=255;
    if(n>=2 && n<11)a[j]=(j==n-2)?255:0;
    if(n<11)border=0;
    win[71-8*j -:8]=8'(a[j]);s+=a[j]*weight[j];
   end
   @(posedge clk);#1;
   if(reset)begin
    for(integer j=0;j<3;j++)q[j]=0;
    if({ov,pixel}!==0)$fatal(1,"Gaussian reset failed");
   end else if(ce)begin
    q[2]=q[1];q[1]=q[0];q[0]={iv,8'(border?0:(s/16))};
    if(ov!==q[2][8] || (ov && pixel!==q[2][7:0]))$fatal(1,"Gaussian arithmetic/latency mismatch n=%0d got=%0d expected=%0d",n,pixel,q[2][7:0]);
    if(ov)checks++;
   end else if({ov,pixel}!==oldout)$fatal(1,"Gaussian CE hold failed");
  end
  if(checks<8500)$fatal(1,"insufficient comparisons");
  $display("PASS GAUSSIAN: %0d independent weighted sum, extremes, impulse, floor, border, CE, valid holes, reset comparisons",checks);$finish;
 end
endmodule
