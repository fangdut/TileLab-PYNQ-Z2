// V1.56: both radii use one 32-row gray store. R8 taps evaluated at its original time.
// V1.55: added seven-point / offset-four response shares existing R16 RAM.
// V1.54 candidate; original valley and directional mean share one window.
// Four opposed-neighbor dark-valley scores in a 17x17 support.
// Rejects one-sided steps; supports dark lines narrower than 16 pixels.
// This is a deterministic contrast feature, not semantic crack recognition.
module shared_window_v156 #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650,R=16)(
 input wire clk,reset,input wire [7:0] gray,
 input wire [23:0] rgb,input wire de,hs,vs,
 output wire [23:0] rgb_out,output wire de_out,hs_out,vs_out,
 output reg [7:0] score=0,output reg [7:0] mean_score=0,output reg [7:0] wide_line_score=0,output reg [3:0] direction_weak=0,output reg [7:0] narrow_score=0,short_score=0);
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
  for(row=0;row<=N;row=row+1)if(row==0 || row==R || row==N || (row>=R-REACH && row<=R+REACH) || row==R+12 || row==R+13)begin
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
reg [11:0] wide7_0_0=0;
wire [11:0] wide7_0_0_next=((({4'b0,shift[16][18]}+{4'b0,shift[16][17]})+({4'b0,shift[16][16]}+{4'b0,shift[16][15]}))+(({4'b0,shift[16][14]}+{4'b0,shift[16][13]})+({4'b0,shift[16][12]}+{4'b0,shift[16][15]})));
reg [11:0] wide7_0_1=0;
wire [11:0] wide7_0_1_next=((({4'b0,shift[12][18]}+{4'b0,shift[12][17]})+({4'b0,shift[12][16]}+{4'b0,shift[12][15]}))+(({4'b0,shift[12][14]}+{4'b0,shift[12][13]})+({4'b0,shift[12][12]}+{4'b0,shift[12][15]})));
reg [11:0] wide7_0_2=0;
wire [11:0] wide7_0_2_next=((({4'b0,shift[20][18]}+{4'b0,shift[20][17]})+({4'b0,shift[20][16]}+{4'b0,shift[20][15]}))+(({4'b0,shift[20][14]}+{4'b0,shift[20][13]})+({4'b0,shift[20][12]}+{4'b0,shift[20][15]})));
wire [7:0] wide7_flank_0=minimum(wide7_0_1[3+:8],wide7_0_2[3+:8]);
wire [7:0] wide7_score_0=(wide7_flank_0>wide7_0_0[3+:8])?wide7_flank_0-wide7_0_0[3+:8]:0;
reg [11:0] wide7_1_0=0;
wire [11:0] wide7_1_0_next=((({4'b0,shift[13][15]}+{4'b0,shift[14][15]})+({4'b0,shift[15][15]}+{4'b0,shift[16][15]}))+(({4'b0,shift[17][15]}+{4'b0,shift[18][15]})+({4'b0,shift[19][15]}+{4'b0,shift[16][15]})));
reg [11:0] wide7_1_1=0;
wire [11:0] wide7_1_1_next=((({4'b0,shift[13][11]}+{4'b0,shift[14][11]})+({4'b0,shift[15][11]}+{4'b0,shift[16][11]}))+(({4'b0,shift[17][11]}+{4'b0,shift[18][11]})+({4'b0,shift[19][11]}+{4'b0,shift[16][11]})));
reg [11:0] wide7_1_2=0;
wire [11:0] wide7_1_2_next=((({4'b0,shift[13][19]}+{4'b0,shift[14][19]})+({4'b0,shift[15][19]}+{4'b0,shift[16][19]}))+(({4'b0,shift[17][19]}+{4'b0,shift[18][19]})+({4'b0,shift[19][19]}+{4'b0,shift[16][19]})));
wire [7:0] wide7_flank_1=minimum(wide7_1_1[3+:8],wide7_1_2[3+:8]);
wire [7:0] wide7_score_1=(wide7_flank_1>wide7_1_0[3+:8])?wide7_flank_1-wide7_1_0[3+:8]:0;
reg [11:0] wide7_2_0=0;
wire [11:0] wide7_2_0_next=((({4'b0,shift[13][18]}+{4'b0,shift[14][17]})+({4'b0,shift[15][16]}+{4'b0,shift[16][15]}))+(({4'b0,shift[17][14]}+{4'b0,shift[18][13]})+({4'b0,shift[19][12]}+{4'b0,shift[16][15]})));
reg [11:0] wide7_2_1=0;
wire [11:0] wide7_2_1_next=((({4'b0,shift[9][14]}+{4'b0,shift[10][13]})+({4'b0,shift[11][12]}+{4'b0,shift[12][11]}))+(({4'b0,shift[13][10]}+{4'b0,shift[14][9]})+({4'b0,shift[15][8]}+{4'b0,shift[12][11]})));
reg [11:0] wide7_2_2=0;
wire [11:0] wide7_2_2_next=((({4'b0,shift[17][22]}+{4'b0,shift[18][21]})+({4'b0,shift[19][20]}+{4'b0,shift[20][19]}))+(({4'b0,shift[21][18]}+{4'b0,shift[22][17]})+({4'b0,shift[23][16]}+{4'b0,shift[20][19]})));
wire [7:0] wide7_flank_2=minimum(wide7_2_1[3+:8],wide7_2_2[3+:8]);
wire [7:0] wide7_score_2=(wide7_flank_2>wide7_2_0[3+:8])?wide7_flank_2-wide7_2_0[3+:8]:0;
reg [11:0] wide7_3_0=0;
wire [11:0] wide7_3_0_next=((({4'b0,shift[19][18]}+{4'b0,shift[18][17]})+({4'b0,shift[17][16]}+{4'b0,shift[16][15]}))+(({4'b0,shift[15][14]}+{4'b0,shift[14][13]})+({4'b0,shift[13][12]}+{4'b0,shift[16][15]})));
reg [11:0] wide7_3_1=0;
wire [11:0] wide7_3_1_next=((({4'b0,shift[15][22]}+{4'b0,shift[14][21]})+({4'b0,shift[13][20]}+{4'b0,shift[12][19]}))+(({4'b0,shift[11][18]}+{4'b0,shift[10][17]})+({4'b0,shift[9][16]}+{4'b0,shift[12][19]})));
reg [11:0] wide7_3_2=0;
wire [11:0] wide7_3_2_next=((({4'b0,shift[23][14]}+{4'b0,shift[22][13]})+({4'b0,shift[21][12]}+{4'b0,shift[20][11]}))+(({4'b0,shift[19][10]}+{4'b0,shift[18][9]})+({4'b0,shift[17][8]}+{4'b0,shift[20][11]})));
wire [7:0] wide7_flank_3=minimum(wide7_3_1[3+:8],wide7_3_2[3+:8]);
wire [7:0] wide7_score_3=(wide7_flank_3>wide7_3_0[3+:8])?wide7_flank_3-wide7_3_0[3+:8]:0;
wire [7:0] wide7_max=maximum(maximum(wide7_score_0,wide7_score_1),maximum(wide7_score_2,wide7_score_3));
reg [11:0] dir7_0_0=0;
wire [11:0] dir7_0_0_next=((({4'b0,shift[14][18]}+{4'b0,shift[14][17]})+({4'b0,shift[14][16]}+{4'b0,shift[14][15]}))+(({4'b0,shift[14][14]}+{4'b0,shift[14][13]})+({4'b0,shift[14][12]}+{4'b0,shift[14][15]})));
reg [11:0] dir7_0_1=0;
wire [11:0] dir7_0_1_next=((({4'b0,shift[18][18]}+{4'b0,shift[18][17]})+({4'b0,shift[18][16]}+{4'b0,shift[18][15]}))+(({4'b0,shift[18][14]}+{4'b0,shift[18][13]})+({4'b0,shift[18][12]}+{4'b0,shift[18][15]})));
wire [7:0] dir7_flank_0=minimum(dir7_0_0[3+:8],dir7_0_1[3+:8]);
wire [7:0] dir7_score_0=(dir7_flank_0>wide7_0_0[3+:8])?dir7_flank_0-wide7_0_0[3+:8]:0;
reg [11:0] dir7_1_0=0;
wire [11:0] dir7_1_0_next=((({4'b0,shift[13][13]}+{4'b0,shift[14][13]})+({4'b0,shift[15][13]}+{4'b0,shift[16][13]}))+(({4'b0,shift[17][13]}+{4'b0,shift[18][13]})+({4'b0,shift[19][13]}+{4'b0,shift[16][13]})));
reg [11:0] dir7_1_1=0;
wire [11:0] dir7_1_1_next=((({4'b0,shift[13][17]}+{4'b0,shift[14][17]})+({4'b0,shift[15][17]}+{4'b0,shift[16][17]}))+(({4'b0,shift[17][17]}+{4'b0,shift[18][17]})+({4'b0,shift[19][17]}+{4'b0,shift[16][17]})));
wire [7:0] dir7_flank_1=minimum(dir7_1_0[3+:8],dir7_1_1[3+:8]);
wire [7:0] dir7_score_1=(dir7_flank_1>wide7_1_0[3+:8])?dir7_flank_1-wide7_1_0[3+:8]:0;
reg [11:0] dir7_2_0=0;
wire [11:0] dir7_2_0_next=((({4'b0,shift[11][16]}+{4'b0,shift[12][15]})+({4'b0,shift[13][14]}+{4'b0,shift[14][13]}))+(({4'b0,shift[15][12]}+{4'b0,shift[16][11]})+({4'b0,shift[17][10]}+{4'b0,shift[14][13]})));
reg [11:0] dir7_2_1=0;
wire [11:0] dir7_2_1_next=((({4'b0,shift[15][20]}+{4'b0,shift[16][19]})+({4'b0,shift[17][18]}+{4'b0,shift[18][17]}))+(({4'b0,shift[19][16]}+{4'b0,shift[20][15]})+({4'b0,shift[21][14]}+{4'b0,shift[18][17]})));
wire [7:0] dir7_flank_2=minimum(dir7_2_0[3+:8],dir7_2_1[3+:8]);
wire [7:0] dir7_score_2=(dir7_flank_2>wide7_2_0[3+:8])?dir7_flank_2-wide7_2_0[3+:8]:0;
reg [11:0] dir7_3_0=0;
wire [11:0] dir7_3_0_next=((({4'b0,shift[17][20]}+{4'b0,shift[16][19]})+({4'b0,shift[15][18]}+{4'b0,shift[14][17]}))+(({4'b0,shift[13][16]}+{4'b0,shift[12][15]})+({4'b0,shift[11][14]}+{4'b0,shift[14][17]})));
reg [11:0] dir7_3_1=0;
wire [11:0] dir7_3_1_next=((({4'b0,shift[21][16]}+{4'b0,shift[20][15]})+({4'b0,shift[19][14]}+{4'b0,shift[18][13]}))+(({4'b0,shift[17][12]}+{4'b0,shift[16][11]})+({4'b0,shift[15][10]}+{4'b0,shift[18][13]})));
wire [7:0] dir7_flank_3=minimum(dir7_3_0[3+:8],dir7_3_1[3+:8]);
wire [7:0] dir7_score_3=(dir7_flank_3>wide7_3_0[3+:8])?dir7_flank_3-wide7_3_0[3+:8]:0;
wire [7:0] n8_horizontal=minimum(shift[24][15],hist[7]);
wire [7:0] n8_vertical=minimum(shift[16][7],shift[32][7]);
wire [7:0] n8_diag1=minimum(shift[16][15],pq);
wire [7:0] n8_diag2=minimum(hist[15],shift[32][15]);
reg [7:0] n8_h=0,n8_v=0,n8_d1=0,n8_d2=0,n8_center=0;reg n8_valid=0;
wire [7:0] n8_shoulder=maximum(maximum(n8_h,n8_v),maximum(n8_d1,n8_d2));
reg [11:0] small7_0_0=0;
wire [11:0] small7_0_0_next=((({4'b0,shift[24][10]}+{4'b0,shift[24][9]})+({4'b0,shift[24][8]}+{4'b0,shift[24][7]}))+(({4'b0,shift[24][6]}+{4'b0,shift[24][5]})+({4'b0,shift[24][4]}+{4'b0,shift[24][7]})));
reg [11:0] small7_0_1=0;
wire [11:0] small7_0_1_next=((({4'b0,shift[22][10]}+{4'b0,shift[22][9]})+({4'b0,shift[22][8]}+{4'b0,shift[22][7]}))+(({4'b0,shift[22][6]}+{4'b0,shift[22][5]})+({4'b0,shift[22][4]}+{4'b0,shift[22][7]})));
reg [11:0] small7_0_2=0;
wire [11:0] small7_0_2_next=((({4'b0,shift[26][10]}+{4'b0,shift[26][9]})+({4'b0,shift[26][8]}+{4'b0,shift[26][7]}))+(({4'b0,shift[26][6]}+{4'b0,shift[26][5]})+({4'b0,shift[26][4]}+{4'b0,shift[26][7]})));
wire [7:0] small7_flank_0=minimum(small7_0_1[3+:8],small7_0_2[3+:8]);
wire [7:0] small7_score_0=(small7_flank_0>small7_0_0[3+:8])?small7_flank_0-small7_0_0[3+:8]:0;
reg [11:0] small7_1_0=0;
wire [11:0] small7_1_0_next=((({4'b0,shift[21][7]}+{4'b0,shift[22][7]})+({4'b0,shift[23][7]}+{4'b0,shift[24][7]}))+(({4'b0,shift[25][7]}+{4'b0,shift[26][7]})+({4'b0,shift[27][7]}+{4'b0,shift[24][7]})));
reg [11:0] small7_1_1=0;
wire [11:0] small7_1_1_next=((({4'b0,shift[21][5]}+{4'b0,shift[22][5]})+({4'b0,shift[23][5]}+{4'b0,shift[24][5]}))+(({4'b0,shift[25][5]}+{4'b0,shift[26][5]})+({4'b0,shift[27][5]}+{4'b0,shift[24][5]})));
reg [11:0] small7_1_2=0;
wire [11:0] small7_1_2_next=((({4'b0,shift[21][9]}+{4'b0,shift[22][9]})+({4'b0,shift[23][9]}+{4'b0,shift[24][9]}))+(({4'b0,shift[25][9]}+{4'b0,shift[26][9]})+({4'b0,shift[27][9]}+{4'b0,shift[24][9]})));
wire [7:0] small7_flank_1=minimum(small7_1_1[3+:8],small7_1_2[3+:8]);
wire [7:0] small7_score_1=(small7_flank_1>small7_1_0[3+:8])?small7_flank_1-small7_1_0[3+:8]:0;
reg [11:0] small7_2_0=0;
wire [11:0] small7_2_0_next=((({4'b0,shift[21][10]}+{4'b0,shift[22][9]})+({4'b0,shift[23][8]}+{4'b0,shift[24][7]}))+(({4'b0,shift[25][6]}+{4'b0,shift[26][5]})+({4'b0,shift[27][4]}+{4'b0,shift[24][7]})));
reg [11:0] small7_2_1=0;
wire [11:0] small7_2_1_next=((({4'b0,shift[19][8]}+{4'b0,shift[20][7]})+({4'b0,shift[21][6]}+{4'b0,shift[22][5]}))+(({4'b0,shift[23][4]}+{4'b0,shift[24][3]})+({4'b0,shift[25][2]}+{4'b0,shift[22][5]})));
reg [11:0] small7_2_2=0;
wire [11:0] small7_2_2_next=((({4'b0,shift[23][12]}+{4'b0,shift[24][11]})+({4'b0,shift[25][10]}+{4'b0,shift[26][9]}))+(({4'b0,shift[27][8]}+{4'b0,shift[28][7]})+({4'b0,shift[29][6]}+{4'b0,shift[26][9]})));
wire [7:0] small7_flank_2=minimum(small7_2_1[3+:8],small7_2_2[3+:8]);
wire [7:0] small7_score_2=(small7_flank_2>small7_2_0[3+:8])?small7_flank_2-small7_2_0[3+:8]:0;
reg [11:0] small7_3_0=0;
wire [11:0] small7_3_0_next=((({4'b0,shift[27][10]}+{4'b0,shift[26][9]})+({4'b0,shift[25][8]}+{4'b0,shift[24][7]}))+(({4'b0,shift[23][6]}+{4'b0,shift[22][5]})+({4'b0,shift[21][4]}+{4'b0,shift[24][7]})));
reg [11:0] small7_3_1=0;
wire [11:0] small7_3_1_next=((({4'b0,shift[25][12]}+{4'b0,shift[24][11]})+({4'b0,shift[23][10]}+{4'b0,shift[22][9]}))+(({4'b0,shift[21][8]}+{4'b0,shift[20][7]})+({4'b0,shift[19][6]}+{4'b0,shift[22][9]})));
reg [11:0] small7_3_2=0;
wire [11:0] small7_3_2_next=((({4'b0,shift[29][8]}+{4'b0,shift[28][7]})+({4'b0,shift[27][6]}+{4'b0,shift[26][5]}))+(({4'b0,shift[25][4]}+{4'b0,shift[24][3]})+({4'b0,shift[23][2]}+{4'b0,shift[26][5]})));
wire [7:0] small7_flank_3=minimum(small7_3_1[3+:8],small7_3_2[3+:8]);
wire [7:0] small7_score_3=(small7_flank_3>small7_3_0[3+:8])?small7_flank_3-small7_3_0[3+:8]:0;
wire [7:0] small7_max=maximum(maximum(small7_score_0,small7_score_1),maximum(small7_score_2,small7_score_3));
 always @(posedge clk)begin
  if(reset)begin x<=0;y<=0;xq<=0;yq<=0;pd<=0;pv<=0;vq<=0;score<=0;mean_score<=0;wide_line_score<=0;direction_weak<=0;pair_valid<=0;narrow_score<=0;short_score<=0;n8_valid<=0;end
  else begin
   pd<=de;pv<=vs;vq<=de;xq<=x;yq<=y;pq<=gray;
   if(vs && !pv)begin x<=0;y<=0;end
   else begin if(de)x<=x+1'b1;else x<=0;if(pd && !de)y<=y+1'b1;end
   small7_0_0<=small7_0_0_next;
   small7_0_1<=small7_0_1_next;
   small7_0_2<=small7_0_2_next;
   small7_1_0<=small7_1_0_next;
   small7_1_1<=small7_1_1_next;
   small7_1_2<=small7_1_2_next;
   small7_2_0<=small7_2_0_next;
   small7_2_1<=small7_2_1_next;
   small7_2_2<=small7_2_2_next;
   small7_3_0<=small7_3_0_next;
   small7_3_1<=small7_3_1_next;
   small7_3_2<=small7_3_2_next;
   n8_h<=n8_horizontal;n8_v<=n8_vertical;n8_d1<=n8_diag1;n8_d2<=n8_diag2;n8_center<=shift[24][7];
   n8_valid<=vq && xq>=16 && yq>=16 && xq<WIDTH && yq<HEIGHT;
   narrow_score<=(n8_valid && n8_shoulder>n8_center)?n8_shoulder-n8_center:0;
   short_score<=n8_valid?small7_max:0;
   dir7_0_0<=dir7_0_0_next;
   dir7_0_1<=dir7_0_1_next;
   dir7_1_0<=dir7_1_0_next;
   dir7_1_1<=dir7_1_1_next;
   dir7_2_0<=dir7_2_0_next;
   dir7_2_1<=dir7_2_1_next;
   dir7_3_0<=dir7_3_0_next;
   dir7_3_1<=dir7_3_1_next;
   wide7_0_0<=wide7_0_0_next;
   wide7_0_1<=wide7_0_1_next;
   wide7_0_2<=wide7_0_2_next;
   wide7_1_0<=wide7_1_0_next;
   wide7_1_1<=wide7_1_1_next;
   wide7_1_2<=wide7_1_2_next;
   wide7_2_0<=wide7_2_0_next;
   wide7_2_1<=wide7_2_1_next;
   wide7_2_2<=wide7_2_2_next;
   wide7_3_0<=wide7_3_0_next;
   wide7_3_1<=wide7_3_1_next;
   wide7_3_2<=wide7_3_2_next;
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
   wide_line_score<=pair_valid?wide7_max:0;
   direction_weak<=pair_valid?{(dir7_score_3>20 || ridge_3>24),(dir7_score_2>20 || ridge_2>24),(dir7_score_1>20 || ridge_1>24),(dir7_score_0>20 || ridge_0>24)}:0;
  end
 end
 // Center is R lines + R pixels before the accepted window bottom-right.
 // Window evaluation takes one additional register cycle after RAM reads.
 wire [26:0] delayed;
 raster_delay #(.WIDTH(27),.WORDS(R*H_TOTAL+R+2)) align(
 .clk(clk),.reset(reset),.din({vs,hs,de,rgb}),.dout(delayed));
 assign {vs_out,hs_out,de_out,rgb_out}=delayed;
endmodule
