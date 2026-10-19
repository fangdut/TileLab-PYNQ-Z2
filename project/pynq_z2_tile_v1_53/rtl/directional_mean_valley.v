// V1.54 candidate; original valley and directional mean share one window.
// Four opposed-neighbor dark-valley scores in a 17x17 support.
// Rejects one-sided steps; supports dark lines narrower than 16 pixels.
// This is a deterministic contrast feature, not semantic crack recognition.
module directional_mean_valley #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650,R=8)(
 input wire clk,reset,input wire [7:0] gray,
 input wire [23:0] rgb,input wire de,hs,vs,
 output wire [23:0] rgb_out,output wire de_out,hs_out,vs_out,
 output reg [7:0] score=0,output reg [7:0] mean_score=0);
 localparam N=2*R;
 localparam HALF=R/2-1, OFFSET=R/4, AVG_SHIFT=(R==8)?3:4, REACH=HALF+OFFSET;
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
  for(row=0;row<=N;row=row+1)if(row==0 || row==R || row==N || (row>=R-REACH && row<=R+REACH))begin
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
 // Shared gray row RAM; additional taps implement integer line averages.
 // R8: seven tangent pixels + center, >>3, flank offset 2.
 // R16: fifteen tangent pixels + center, >>4, flank offset 4.
 // Explicit tap wires keep simulation and synthesis sensitivity identical.
 wire [11:0] tap_0_0[0:15];
 genvar tap_index_0_0;
 generate for(tap_index_0_0=0;tap_index_0_0<16;tap_index_0_0=tap_index_0_0+1)begin:taps_0_0
  localparam K=tap_index_0_0-HALF;
  if(tap_index_0_0<2*HALF+1)assign tap_0_0[tap_index_0_0]={4'b0,shift[R+(0)*OFFSET+(0)*K][R-1-(0)*OFFSET-(1)*K]};
  else if(tap_index_0_0==2*HALF+1)assign tap_0_0[tap_index_0_0]={4'b0,shift[R+(0)*OFFSET][R-1-(0)*OFFSET]};
  else assign tap_0_0[tap_index_0_0]=0;
 end endgenerate
 reg [11:0] sum_0_0=0;
 wire [11:0] next_0_0=((((tap_0_0[0]+tap_0_0[1])+(tap_0_0[2]+tap_0_0[3]))+((tap_0_0[4]+tap_0_0[5])+(tap_0_0[6]+tap_0_0[7])))+(((tap_0_0[8]+tap_0_0[9])+(tap_0_0[10]+tap_0_0[11]))+((tap_0_0[12]+tap_0_0[13])+(tap_0_0[14]+tap_0_0[15]))));
 wire [11:0] tap_0_1[0:15];
 genvar tap_index_0_1;
 generate for(tap_index_0_1=0;tap_index_0_1<16;tap_index_0_1=tap_index_0_1+1)begin:taps_0_1
  localparam K=tap_index_0_1-HALF;
  if(tap_index_0_1<2*HALF+1)assign tap_0_1[tap_index_0_1]={4'b0,shift[R+(-1)*OFFSET+(0)*K][R-1-(0)*OFFSET-(1)*K]};
  else if(tap_index_0_1==2*HALF+1)assign tap_0_1[tap_index_0_1]={4'b0,shift[R+(-1)*OFFSET][R-1-(0)*OFFSET]};
  else assign tap_0_1[tap_index_0_1]=0;
 end endgenerate
 reg [11:0] sum_0_1=0;
 wire [11:0] next_0_1=((((tap_0_1[0]+tap_0_1[1])+(tap_0_1[2]+tap_0_1[3]))+((tap_0_1[4]+tap_0_1[5])+(tap_0_1[6]+tap_0_1[7])))+(((tap_0_1[8]+tap_0_1[9])+(tap_0_1[10]+tap_0_1[11]))+((tap_0_1[12]+tap_0_1[13])+(tap_0_1[14]+tap_0_1[15]))));
 wire [11:0] tap_0_2[0:15];
 genvar tap_index_0_2;
 generate for(tap_index_0_2=0;tap_index_0_2<16;tap_index_0_2=tap_index_0_2+1)begin:taps_0_2
  localparam K=tap_index_0_2-HALF;
  if(tap_index_0_2<2*HALF+1)assign tap_0_2[tap_index_0_2]={4'b0,shift[R+(1)*OFFSET+(0)*K][R-1-(0)*OFFSET-(1)*K]};
  else if(tap_index_0_2==2*HALF+1)assign tap_0_2[tap_index_0_2]={4'b0,shift[R+(1)*OFFSET][R-1-(0)*OFFSET]};
  else assign tap_0_2[tap_index_0_2]=0;
 end endgenerate
 reg [11:0] sum_0_2=0;
 wire [11:0] next_0_2=((((tap_0_2[0]+tap_0_2[1])+(tap_0_2[2]+tap_0_2[3]))+((tap_0_2[4]+tap_0_2[5])+(tap_0_2[6]+tap_0_2[7])))+(((tap_0_2[8]+tap_0_2[9])+(tap_0_2[10]+tap_0_2[11]))+((tap_0_2[12]+tap_0_2[13])+(tap_0_2[14]+tap_0_2[15]))));
 wire [7:0] flank_0=minimum(sum_0_1[AVG_SHIFT+:8],sum_0_2[AVG_SHIFT+:8]);
 wire [7:0] ridge_0=(flank_0>sum_0_0[AVG_SHIFT+:8])?flank_0-sum_0_0[AVG_SHIFT+:8]:0;
 wire [11:0] tap_1_0[0:15];
 genvar tap_index_1_0;
 generate for(tap_index_1_0=0;tap_index_1_0<16;tap_index_1_0=tap_index_1_0+1)begin:taps_1_0
  localparam K=tap_index_1_0-HALF;
  if(tap_index_1_0<2*HALF+1)assign tap_1_0[tap_index_1_0]={4'b0,shift[R+(0)*OFFSET+(1)*K][R-1-(0)*OFFSET-(0)*K]};
  else if(tap_index_1_0==2*HALF+1)assign tap_1_0[tap_index_1_0]={4'b0,shift[R+(0)*OFFSET][R-1-(0)*OFFSET]};
  else assign tap_1_0[tap_index_1_0]=0;
 end endgenerate
 reg [11:0] sum_1_0=0;
 wire [11:0] next_1_0=((((tap_1_0[0]+tap_1_0[1])+(tap_1_0[2]+tap_1_0[3]))+((tap_1_0[4]+tap_1_0[5])+(tap_1_0[6]+tap_1_0[7])))+(((tap_1_0[8]+tap_1_0[9])+(tap_1_0[10]+tap_1_0[11]))+((tap_1_0[12]+tap_1_0[13])+(tap_1_0[14]+tap_1_0[15]))));
 wire [11:0] tap_1_1[0:15];
 genvar tap_index_1_1;
 generate for(tap_index_1_1=0;tap_index_1_1<16;tap_index_1_1=tap_index_1_1+1)begin:taps_1_1
  localparam K=tap_index_1_1-HALF;
  if(tap_index_1_1<2*HALF+1)assign tap_1_1[tap_index_1_1]={4'b0,shift[R+(0)*OFFSET+(1)*K][R-1-(1)*OFFSET-(0)*K]};
  else if(tap_index_1_1==2*HALF+1)assign tap_1_1[tap_index_1_1]={4'b0,shift[R+(0)*OFFSET][R-1-(1)*OFFSET]};
  else assign tap_1_1[tap_index_1_1]=0;
 end endgenerate
 reg [11:0] sum_1_1=0;
 wire [11:0] next_1_1=((((tap_1_1[0]+tap_1_1[1])+(tap_1_1[2]+tap_1_1[3]))+((tap_1_1[4]+tap_1_1[5])+(tap_1_1[6]+tap_1_1[7])))+(((tap_1_1[8]+tap_1_1[9])+(tap_1_1[10]+tap_1_1[11]))+((tap_1_1[12]+tap_1_1[13])+(tap_1_1[14]+tap_1_1[15]))));
 wire [11:0] tap_1_2[0:15];
 genvar tap_index_1_2;
 generate for(tap_index_1_2=0;tap_index_1_2<16;tap_index_1_2=tap_index_1_2+1)begin:taps_1_2
  localparam K=tap_index_1_2-HALF;
  if(tap_index_1_2<2*HALF+1)assign tap_1_2[tap_index_1_2]={4'b0,shift[R+(0)*OFFSET+(1)*K][R-1-(-1)*OFFSET-(0)*K]};
  else if(tap_index_1_2==2*HALF+1)assign tap_1_2[tap_index_1_2]={4'b0,shift[R+(0)*OFFSET][R-1-(-1)*OFFSET]};
  else assign tap_1_2[tap_index_1_2]=0;
 end endgenerate
 reg [11:0] sum_1_2=0;
 wire [11:0] next_1_2=((((tap_1_2[0]+tap_1_2[1])+(tap_1_2[2]+tap_1_2[3]))+((tap_1_2[4]+tap_1_2[5])+(tap_1_2[6]+tap_1_2[7])))+(((tap_1_2[8]+tap_1_2[9])+(tap_1_2[10]+tap_1_2[11]))+((tap_1_2[12]+tap_1_2[13])+(tap_1_2[14]+tap_1_2[15]))));
 wire [7:0] flank_1=minimum(sum_1_1[AVG_SHIFT+:8],sum_1_2[AVG_SHIFT+:8]);
 wire [7:0] ridge_1=(flank_1>sum_1_0[AVG_SHIFT+:8])?flank_1-sum_1_0[AVG_SHIFT+:8]:0;
 wire [11:0] tap_2_0[0:15];
 genvar tap_index_2_0;
 generate for(tap_index_2_0=0;tap_index_2_0<16;tap_index_2_0=tap_index_2_0+1)begin:taps_2_0
  localparam K=tap_index_2_0-HALF;
  if(tap_index_2_0<2*HALF+1)assign tap_2_0[tap_index_2_0]={4'b0,shift[R+(0)*OFFSET+(1)*K][R-1-(0)*OFFSET-(1)*K]};
  else if(tap_index_2_0==2*HALF+1)assign tap_2_0[tap_index_2_0]={4'b0,shift[R+(0)*OFFSET][R-1-(0)*OFFSET]};
  else assign tap_2_0[tap_index_2_0]=0;
 end endgenerate
 reg [11:0] sum_2_0=0;
 wire [11:0] next_2_0=((((tap_2_0[0]+tap_2_0[1])+(tap_2_0[2]+tap_2_0[3]))+((tap_2_0[4]+tap_2_0[5])+(tap_2_0[6]+tap_2_0[7])))+(((tap_2_0[8]+tap_2_0[9])+(tap_2_0[10]+tap_2_0[11]))+((tap_2_0[12]+tap_2_0[13])+(tap_2_0[14]+tap_2_0[15]))));
 wire [11:0] tap_2_1[0:15];
 genvar tap_index_2_1;
 generate for(tap_index_2_1=0;tap_index_2_1<16;tap_index_2_1=tap_index_2_1+1)begin:taps_2_1
  localparam K=tap_index_2_1-HALF;
  if(tap_index_2_1<2*HALF+1)assign tap_2_1[tap_index_2_1]={4'b0,shift[R+(-1)*OFFSET+(1)*K][R-1-(1)*OFFSET-(1)*K]};
  else if(tap_index_2_1==2*HALF+1)assign tap_2_1[tap_index_2_1]={4'b0,shift[R+(-1)*OFFSET][R-1-(1)*OFFSET]};
  else assign tap_2_1[tap_index_2_1]=0;
 end endgenerate
 reg [11:0] sum_2_1=0;
 wire [11:0] next_2_1=((((tap_2_1[0]+tap_2_1[1])+(tap_2_1[2]+tap_2_1[3]))+((tap_2_1[4]+tap_2_1[5])+(tap_2_1[6]+tap_2_1[7])))+(((tap_2_1[8]+tap_2_1[9])+(tap_2_1[10]+tap_2_1[11]))+((tap_2_1[12]+tap_2_1[13])+(tap_2_1[14]+tap_2_1[15]))));
 wire [11:0] tap_2_2[0:15];
 genvar tap_index_2_2;
 generate for(tap_index_2_2=0;tap_index_2_2<16;tap_index_2_2=tap_index_2_2+1)begin:taps_2_2
  localparam K=tap_index_2_2-HALF;
  if(tap_index_2_2<2*HALF+1)assign tap_2_2[tap_index_2_2]={4'b0,shift[R+(1)*OFFSET+(1)*K][R-1-(-1)*OFFSET-(1)*K]};
  else if(tap_index_2_2==2*HALF+1)assign tap_2_2[tap_index_2_2]={4'b0,shift[R+(1)*OFFSET][R-1-(-1)*OFFSET]};
  else assign tap_2_2[tap_index_2_2]=0;
 end endgenerate
 reg [11:0] sum_2_2=0;
 wire [11:0] next_2_2=((((tap_2_2[0]+tap_2_2[1])+(tap_2_2[2]+tap_2_2[3]))+((tap_2_2[4]+tap_2_2[5])+(tap_2_2[6]+tap_2_2[7])))+(((tap_2_2[8]+tap_2_2[9])+(tap_2_2[10]+tap_2_2[11]))+((tap_2_2[12]+tap_2_2[13])+(tap_2_2[14]+tap_2_2[15]))));
 wire [7:0] flank_2=minimum(sum_2_1[AVG_SHIFT+:8],sum_2_2[AVG_SHIFT+:8]);
 wire [7:0] ridge_2=(flank_2>sum_2_0[AVG_SHIFT+:8])?flank_2-sum_2_0[AVG_SHIFT+:8]:0;
 wire [11:0] tap_3_0[0:15];
 genvar tap_index_3_0;
 generate for(tap_index_3_0=0;tap_index_3_0<16;tap_index_3_0=tap_index_3_0+1)begin:taps_3_0
  localparam K=tap_index_3_0-HALF;
  if(tap_index_3_0<2*HALF+1)assign tap_3_0[tap_index_3_0]={4'b0,shift[R+(0)*OFFSET+(-1)*K][R-1-(0)*OFFSET-(1)*K]};
  else if(tap_index_3_0==2*HALF+1)assign tap_3_0[tap_index_3_0]={4'b0,shift[R+(0)*OFFSET][R-1-(0)*OFFSET]};
  else assign tap_3_0[tap_index_3_0]=0;
 end endgenerate
 reg [11:0] sum_3_0=0;
 wire [11:0] next_3_0=((((tap_3_0[0]+tap_3_0[1])+(tap_3_0[2]+tap_3_0[3]))+((tap_3_0[4]+tap_3_0[5])+(tap_3_0[6]+tap_3_0[7])))+(((tap_3_0[8]+tap_3_0[9])+(tap_3_0[10]+tap_3_0[11]))+((tap_3_0[12]+tap_3_0[13])+(tap_3_0[14]+tap_3_0[15]))));
 wire [11:0] tap_3_1[0:15];
 genvar tap_index_3_1;
 generate for(tap_index_3_1=0;tap_index_3_1<16;tap_index_3_1=tap_index_3_1+1)begin:taps_3_1
  localparam K=tap_index_3_1-HALF;
  if(tap_index_3_1<2*HALF+1)assign tap_3_1[tap_index_3_1]={4'b0,shift[R+(-1)*OFFSET+(-1)*K][R-1-(-1)*OFFSET-(1)*K]};
  else if(tap_index_3_1==2*HALF+1)assign tap_3_1[tap_index_3_1]={4'b0,shift[R+(-1)*OFFSET][R-1-(-1)*OFFSET]};
  else assign tap_3_1[tap_index_3_1]=0;
 end endgenerate
 reg [11:0] sum_3_1=0;
 wire [11:0] next_3_1=((((tap_3_1[0]+tap_3_1[1])+(tap_3_1[2]+tap_3_1[3]))+((tap_3_1[4]+tap_3_1[5])+(tap_3_1[6]+tap_3_1[7])))+(((tap_3_1[8]+tap_3_1[9])+(tap_3_1[10]+tap_3_1[11]))+((tap_3_1[12]+tap_3_1[13])+(tap_3_1[14]+tap_3_1[15]))));
 wire [11:0] tap_3_2[0:15];
 genvar tap_index_3_2;
 generate for(tap_index_3_2=0;tap_index_3_2<16;tap_index_3_2=tap_index_3_2+1)begin:taps_3_2
  localparam K=tap_index_3_2-HALF;
  if(tap_index_3_2<2*HALF+1)assign tap_3_2[tap_index_3_2]={4'b0,shift[R+(1)*OFFSET+(-1)*K][R-1-(1)*OFFSET-(1)*K]};
  else if(tap_index_3_2==2*HALF+1)assign tap_3_2[tap_index_3_2]={4'b0,shift[R+(1)*OFFSET][R-1-(1)*OFFSET]};
  else assign tap_3_2[tap_index_3_2]=0;
 end endgenerate
 reg [11:0] sum_3_2=0;
 wire [11:0] next_3_2=((((tap_3_2[0]+tap_3_2[1])+(tap_3_2[2]+tap_3_2[3]))+((tap_3_2[4]+tap_3_2[5])+(tap_3_2[6]+tap_3_2[7])))+(((tap_3_2[8]+tap_3_2[9])+(tap_3_2[10]+tap_3_2[11]))+((tap_3_2[12]+tap_3_2[13])+(tap_3_2[14]+tap_3_2[15]))));
 wire [7:0] flank_3=minimum(sum_3_1[AVG_SHIFT+:8],sum_3_2[AVG_SHIFT+:8]);
 wire [7:0] ridge_3=(flank_3>sum_3_0[AVG_SHIFT+:8])?flank_3-sum_3_0[AVG_SHIFT+:8]:0;
 wire [7:0] mean_max=maximum(maximum(ridge_0,ridge_1),maximum(ridge_2,ridge_3));
 always @(posedge clk)begin
  if(reset)begin x<=0;y<=0;xq<=0;yq<=0;pd<=0;pv<=0;vq<=0;score<=0;mean_score<=0;pair_valid<=0;end
  else begin
   pd<=de;pv<=vs;vq<=de;xq<=x;yq<=y;pq<=gray;
   if(vs && !pv)begin x<=0;y<=0;end
   else begin if(de)x<=x+1'b1;else x<=0;if(pd && !de)y<=y+1'b1;end
   sum_0_0<=next_0_0;
   sum_0_1<=next_0_1;
   sum_0_2<=next_0_2;
   sum_1_0<=next_1_0;
   sum_1_1<=next_1_1;
   sum_1_2<=next_1_2;
   sum_2_0<=next_2_0;
   sum_2_1<=next_2_1;
   sum_2_2<=next_2_2;
   sum_3_0<=next_3_0;
   sum_3_1<=next_3_1;
   sum_3_2<=next_3_2;
   pair_h<=horizontal;pair_v<=vertical;pair_d1<=diag1;pair_d2<=diag2;center_q<=center;
   pair_valid<=vq && xq>=N && yq>=N && xq<WIDTH && yq<HEIGHT;
   score<=(pair_valid && shoulder>center_q)?shoulder-center_q:0;
   mean_score<=pair_valid?mean_max:0;
  end
 end
 // Center is R lines + R pixels before the accepted window bottom-right.
 // Window evaluation takes one additional register cycle after RAM reads.
 wire [26:0] delayed;
 raster_delay #(.WIDTH(27),.WORDS(R*H_TOTAL+R+2)) align(
 .clk(clk),.reset(reset),.din({vs,hs,de,rgb}),.dout(delayed));
 assign {vs_out,hs_out,de_out,rgb_out}=delayed;
endmodule
