// Pixel-domain global box. The preceding complete frame supplies the box;
// a changed configuration, incomplete/empty frame or reset invalidates it.
// No additional pipeline stage; the caller registers rgb_out as before.
module bbox_overlay #(parameter WIDTH=1280,HEIGHT=720)(
 input wire clk,reset,de,vs,mask,enable,
 input wire [31:0] config_word,
 input wire [23:0] rgb_in,
 output wire [23:0] rgb_out);
 reg pd=0,pv=0,started=0,box_valid=0;
 reg [15:0] x=0,y=0,xmin=0,ymin=0,xmax=0,ymax=0;
 reg [15:0] bx0=0,by0=0,bx1=0,by1=0;
 reg [31:0] pixels=0,count=0,frame_config=0;
 always @(posedge clk)begin
  if(reset)begin
   pd<=0;pv<=0;started<=0;box_valid<=0;x<=0;y<=0;pixels<=0;count<=0;
   xmin<=0;ymin<=0;xmax<=0;ymax<=0;bx0<=0;by0<=0;bx1<=0;by1<=0;frame_config<=0;
  end else begin
   pd<=de;pv<=vs;
   if(vs && !pv)begin
    box_valid<=started && pixels==WIDTH*HEIGHT && count!=0 && frame_config==config_word &&
      (frame_config[17:16]!=3 || (count>=32 && ((xmax-xmin)>=23 || (ymax-ymin)>=23)));
    bx0<=xmin;by0<=ymin;bx1<=xmax;by1<=ymax;
    started<=1;x<=0;y<=0;pixels<=0;count<=0;
   end else begin
    if(de)begin
     x<=x+1'b1;pixels<=pixels+1'b1;
     if(pixels==0)frame_config<=config_word;
     if(mask && x<WIDTH && y<HEIGHT)begin
      count<=count+1'b1;
      if(count==0)begin xmin<=x;xmax<=x;ymin<=y;ymax<=y;end
      else begin
       if(x<xmin)xmin<=x;if(x>xmax)xmax<=x;
       if(y<ymin)ymin<=y;if(y>ymax)ymax<=y;
      end
     end
    end else x<=0;
    if(pd && !de)y<=y+1'b1;
   end
  end
 end
 wire on_edge=((x==bx0 || x==bx1) && y>=by0 && y<=by1) ||
              ((y==by0 || y==by1) && x>=bx0 && x<=bx1);
 // Native RBG bus: pure red. Coordinates still refer to the preceding frame.
 assign rgb_out=(de && enable && box_valid && on_edge)?24'hff0000:rgb_in;
endmodule
