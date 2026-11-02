// Reusable 8-bit, 3x3 causal window. Packed order: a,b,c,d,e,f,g,h,i.
// Each accepted input (x,y) is window bottom-right; center is (x-1,y-1).
// ce pauses ALL state; in_valid holes do not consume pixels. No AXIS ready port.
// Two synchronous read-first BRAM line stores; RAM contents need no reset.
module window3x3 #(parameter WIDTH=1280)(
 input wire clk,reset,ce,in_valid, input wire [7:0] pixel_in,
 input wire [15:0] in_x,in_y,
 output reg out_valid=0, output reg [15:0] out_x=0,out_y=0,
 output reg [71:0] window=0, output reg border=1);
 (* ram_style="block" *) reg [7:0] line1[0:WIDTH-1];
 (* ram_style="block" *) reg [7:0] line2[0:WIDTH-1];
 reg [7:0] r1,r2,pq; reg vq=0; reg [15:0] xq=0,yq=0;
 reg [7:0] a0=0,a1=0,b0=0,b1=0,c0=0,c1=0;
 // Pixel-history/window DATA has no runtime reset. Only validity/coordinates reset;
 // x=0 rebuilds horizontal history before any interior sample. This also prevents
 // synthesis from absorbing a resettable data register into BRAM RSTREG.
 // Do not gate RAM enables directly with the asynchronous-asserting reset bridge.
 // During reset, harmless stale writes are allowed; valid/border mask the data,
 // and two incoming rows fully replace it before any interior window is used.
 // Delayed line2 write uses the OLD line1 value, not the incoming row.
 always @(posedge clk) if(ce) begin
  if(in_valid && in_x<WIDTH) begin
   r1<=line1[in_x];r2<=line2[in_x];line1[in_x]<=pixel_in;
  end
  if(vq && xq<WIDTH) line2[xq]<=r1;
 end
 always @(posedge clk) begin
  if(reset) begin
   vq<=0;out_valid<=0;border<=1;
   xq<=0;yq<=0;out_x<=0;out_y<=0;pq<=0;
  end else if(ce) begin
   vq<=in_valid; xq<=in_x;yq<=in_y;pq<=pixel_in;
   out_valid<=vq;out_x<=xq;out_y<=yq;border<=(xq<2 || yq<2);
   if(vq) begin
    if(xq==0) begin
     a0<=0;a1<=r2;b0<=0;b1<=r1;c0<=0;c1<=pq;
     window<={16'b0,r2,16'b0,r1,16'b0,pq};
    end else begin
     a0<=a1;a1<=r2;b0<=b1;b1<=r1;c0<=c1;c1<=pq;
     window<={a0,a1,r2,b0,b1,r1,c0,c1,pq};
    end
   end
  end
 end
endmodule
