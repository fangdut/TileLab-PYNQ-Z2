`timescale 1ns/1ps
module tb_sobel3x3;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,ce=1,iv=0,border=0;reg [71:0] win=0;
 wire ov;wire [7:0] edgep;wire [10:0] mag;
 sobel3x3 dut(clk,reset,ce,iv,border,win,ov,edgep,mag);
 integer a[0:8],gx,gy,s,checks=0;reg [19:0] q[0:2];reg [19:0] oldout;
 initial begin
  for(integer j=0;j<3;j++)q[j]=0;
  repeat(3) @(negedge clk);reset=0;
  for(integer n=0;n<10004;n++) begin
   @(negedge clk);oldout={ov,mag,edgep};ce=(n<8)?1:($urandom_range(0,3)!=0);iv=n<10000;border=(n%13==0);
   for(integer j=0;j<9;j++) a[j]=$urandom_range(0,255);
   if(n==0)begin for(integer j=0;j<9;j++)a[j]=0;border=0;end
   if(n==1)begin for(integer j=0;j<9;j++)a[j]=255;border=0;end
   if(n>=2 && n<=5)begin
    for(integer j=0;j<9;j++)begin
     if(n==2)a[j]=(j%3==2)?255:0;
     if(n==3)a[j]=(j%3==0)?255:0;
     if(n==4)a[j]=(j/3==2)?255:0;
     if(n==5)a[j]=(j/3==0)?255:0;
    end
    border=0;
   end
   win={8'(a[0]),8'(a[1]),8'(a[2]),8'(a[3]),8'(a[4]),8'(a[5]),8'(a[6]),8'(a[7]),8'(a[8])};
   gx=a[2]+2*a[5]+a[8]-a[0]-2*a[3]-a[6];gy=a[6]+2*a[7]+a[8]-a[0]-2*a[1]-a[2];
   s=border?0:((gx<0)?-gx:gx)+((gy<0)?-gy:gy);
   @(posedge clk);#1;
   if(ce)begin
    q[2]=q[1];q[1]=q[0];q[0]={iv,11'(s),8'((s>255)?255:s)};
    if(ov!==q[2][19] || (ov && {mag,edgep}!==q[2][18:0]))$fatal(1,"Sobel arithmetic/latency mismatch n=%0d",n);
    if(ov)checks++;
   end else if({ov,mag,edgep}!==oldout)$fatal(1,"Sobel CE hold failed");
  end
  if(checks<7000)$fatal(1,"insufficient comparisons");
  $display("PASS SOBEL: %0d signed-gradient, magnitude, saturation, border, CE comparisons",checks);$finish;
 end
endmodule
