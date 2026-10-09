// Four opposed-neighbor dark-valley scores in a 17x17 support.
// Rejects one-sided steps; supports dark lines narrower than 16 pixels.
// This is a deterministic contrast feature, not semantic crack recognition.
module directional_valley #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650,R=8)(
 input wire clk,reset,input wire [7:0] gray,
 input wire [23:0] rgb,input wire de,hs,vs,
 output wire [23:0] rgb_out,output wire de_out,hs_out,vs_out,
 output reg [7:0] score=0);
 localparam N=2*R;
 reg [15:0] x=0,y=0,xq=0,yq=0;reg pd=0,pv=0,vq=0;reg [7:0] pq;
 wire [7:0] hist[0:N-1];
 genvar k;
 generate for(k=0;k<N;k=k+1)begin: rows
  (* ram_style="block" *) reg [7:0] mem[0:WIDTH-1];
  reg [7:0] q;
  always @(posedge clk)begin
   if(de && x<WIDTH)q<=mem[x];
   if(k==0)begin if(de && x<WIDTH)mem[x]<=gray;end
   else begin if(vq && xq<WIDTH)mem[xq]<=hist[k-1];end
  end
  assign hist[k]=q;
 end endgenerate
 reg [7:0] shift[0:N][0:N-1];
 integer row,col;
 // Only validity is reset. Horizontal history is rebuilt at each line start.
 always @(posedge clk)if(vq)begin
  for(row=0;row<=N;row=row+1)if(row==0 || row==R || row==N)begin
   shift[row][0]<=(row==N)?pq:hist[N-1-row];
   for(col=1;col<N;col=col+1)shift[row][col]<=(xq==0)?0:shift[row][col-1];
  end
 end
 function [7:0] minimum(input [7:0] a,b);begin minimum=(a<b)?a:b;end endfunction
 function [7:0] maximum(input [7:0] a,b);begin maximum=(a>b)?a:b;end endfunction
 wire [7:0] center=shift[R][R-1];
 wire [7:0] horizontal=minimum(shift[R][N-1],hist[R-1]);
 wire [7:0] vertical=minimum(shift[0][R-1],shift[N][R-1]);
 wire [7:0] diag1=minimum(shift[0][N-1],pq);
 wire [7:0] diag2=minimum(hist[N-1],shift[N][N-1]);
 reg [7:0] pair_h=0,pair_v=0,pair_d1=0,pair_d2=0,center_q=0;reg pair_valid=0;
 wire [7:0] shoulder=maximum(maximum(pair_h,pair_v),maximum(pair_d1,pair_d2));
 always @(posedge clk)begin
  if(reset)begin x<=0;y<=0;xq<=0;yq<=0;pd<=0;pv<=0;vq<=0;score<=0;pair_valid<=0;end
  else begin
   pd<=de;pv<=vs;vq<=de;xq<=x;yq<=y;pq<=gray;
   if(vs && !pv)begin x<=0;y<=0;end
   else begin if(de)x<=x+1'b1;else x<=0;if(pd && !de)y<=y+1'b1;end
   pair_h<=horizontal;pair_v<=vertical;pair_d1<=diag1;pair_d2<=diag2;center_q<=center;
   pair_valid<=vq && xq>=N && yq>=N && xq<WIDTH && yq<HEIGHT;
   score<=(pair_valid && shoulder>center_q)?shoulder-center_q:0;
  end
 end
 // Center is R lines + R pixels before the accepted window bottom-right.
 // Window evaluation takes one additional register cycle after RAM reads.
 wire [26:0] delayed;
 raster_delay #(.WIDTH(27),.WORDS(R*H_TOTAL+R+2)) align(
 .clk(clk),.reset(reset),.din({vs,hs,de,rgb}),.dout(delayed));
 assign {vs_out,hs_out,de_out,rgb_out}=delayed;
endmodule
