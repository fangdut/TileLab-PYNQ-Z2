// V1.56: both radii use one 32-row gray store. R8 taps evaluated at its original time.
// V1.55: added seven-point / offset-four response shares existing R16 RAM.
// V1.54 candidate; original valley and directional mean share one window.
// Four opposed-neighbor dark-valley scores in a 17x17 support.
// Rejects one-sided steps; supports dark lines narrower than 16 pixels.
// This is a deterministic contrast feature, not semantic crack recognition.
module boost_feature_window_v156 #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650,R=16)(
 input wire clk,reset,input wire [7:0] gray,
 input wire [23:0] rgb,input wire de,hs,vs,
 output wire [23:0] rgb_out,output wire de_out,hs_out,vs_out,
 output reg [7:0] score=0,output reg [7:0] mean_score=0,output reg [7:0] wide_line_score=0,output reg [3:0] direction_weak=0,output reg [7:0] narrow_score=0,short_score=0,output reg [87:0] features_hi=0,output reg features_valid=0);
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
  for(row=0;row<=N;row=row+1)if(row>=0 && row<=N)begin
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
function [7:0] abs8(input [7:0] a,b);begin abs8=(a>b)?a-b:b-a;end endfunction
reg [11:0] long8_0_0=0;
wire [11:0] long8_0_0_next=(((({4'b0,shift[8][22]}+{4'b0,shift[8][21]})+({4'b0,shift[8][20]}+{4'b0,shift[8][19]}))+(({4'b0,shift[8][18]}+{4'b0,shift[8][17]})+({4'b0,shift[8][16]}+{4'b0,shift[8][15]})))+((({4'b0,shift[8][14]}+{4'b0,shift[8][13]})+({4'b0,shift[8][12]}+{4'b0,shift[8][11]}))+(({4'b0,shift[8][10]}+{4'b0,shift[8][9]})+({4'b0,shift[8][8]}+{4'b0,shift[8][15]}))));
reg [11:0] long8_0_1=0;
wire [11:0] long8_0_1_next=(((({4'b0,shift[24][22]}+{4'b0,shift[24][21]})+({4'b0,shift[24][20]}+{4'b0,shift[24][19]}))+(({4'b0,shift[24][18]}+{4'b0,shift[24][17]})+({4'b0,shift[24][16]}+{4'b0,shift[24][15]})))+((({4'b0,shift[24][14]}+{4'b0,shift[24][13]})+({4'b0,shift[24][12]}+{4'b0,shift[24][11]}))+(({4'b0,shift[24][10]}+{4'b0,shift[24][9]})+({4'b0,shift[24][8]}+{4'b0,shift[24][15]}))));
wire [7:0] long8_flank_0=minimum(long8_0_0[4+:8],long8_0_1[4+:8]);
wire [7:0] long8_score_0=(long8_flank_0>sum_0_0[4+:8])?long8_flank_0-sum_0_0[4+:8]:0;
reg [11:0] noise_0=0;
wire [11:0] noise_0_next=(((({4'b0,abs8(shift[14][19],shift[14][18])}+{4'b0,abs8(shift[14][18],shift[14][17])})+({4'b0,abs8(shift[14][17],shift[14][16])}+{4'b0,abs8(shift[14][16],shift[14][15])}))+(({4'b0,abs8(shift[14][15],shift[14][14])}+{4'b0,abs8(shift[14][14],shift[14][13])})+({4'b0,abs8(shift[14][13],shift[14][12])}+{4'b0,abs8(shift[14][12],shift[14][11])})))+((({4'b0,abs8(shift[18][19],shift[18][18])}+{4'b0,abs8(shift[18][18],shift[18][17])})+({4'b0,abs8(shift[18][17],shift[18][16])}+{4'b0,abs8(shift[18][16],shift[18][15])}))+(({4'b0,abs8(shift[18][15],shift[18][14])}+{4'b0,abs8(shift[18][14],shift[18][13])})+({4'b0,abs8(shift[18][13],shift[18][12])}+{4'b0,abs8(shift[18][12],shift[18][11])}))));
reg [11:0] long8_1_0=0;
wire [11:0] long8_1_0_next=(((({4'b0,shift[9][7]}+{4'b0,shift[10][7]})+({4'b0,shift[11][7]}+{4'b0,shift[12][7]}))+(({4'b0,shift[13][7]}+{4'b0,shift[14][7]})+({4'b0,shift[15][7]}+{4'b0,shift[16][7]})))+((({4'b0,shift[17][7]}+{4'b0,shift[18][7]})+({4'b0,shift[19][7]}+{4'b0,shift[20][7]}))+(({4'b0,shift[21][7]}+{4'b0,shift[22][7]})+({4'b0,shift[23][7]}+{4'b0,shift[16][7]}))));
reg [11:0] long8_1_1=0;
wire [11:0] long8_1_1_next=(((({4'b0,shift[9][23]}+{4'b0,shift[10][23]})+({4'b0,shift[11][23]}+{4'b0,shift[12][23]}))+(({4'b0,shift[13][23]}+{4'b0,shift[14][23]})+({4'b0,shift[15][23]}+{4'b0,shift[16][23]})))+((({4'b0,shift[17][23]}+{4'b0,shift[18][23]})+({4'b0,shift[19][23]}+{4'b0,shift[20][23]}))+(({4'b0,shift[21][23]}+{4'b0,shift[22][23]})+({4'b0,shift[23][23]}+{4'b0,shift[16][23]}))));
wire [7:0] long8_flank_1=minimum(long8_1_0[4+:8],long8_1_1[4+:8]);
wire [7:0] long8_score_1=(long8_flank_1>sum_1_0[4+:8])?long8_flank_1-sum_1_0[4+:8]:0;
reg [11:0] noise_1=0;
wire [11:0] noise_1_next=(((({4'b0,abs8(shift[12][13],shift[13][13])}+{4'b0,abs8(shift[13][13],shift[14][13])})+({4'b0,abs8(shift[14][13],shift[15][13])}+{4'b0,abs8(shift[15][13],shift[16][13])}))+(({4'b0,abs8(shift[16][13],shift[17][13])}+{4'b0,abs8(shift[17][13],shift[18][13])})+({4'b0,abs8(shift[18][13],shift[19][13])}+{4'b0,abs8(shift[19][13],shift[20][13])})))+((({4'b0,abs8(shift[12][17],shift[13][17])}+{4'b0,abs8(shift[13][17],shift[14][17])})+({4'b0,abs8(shift[14][17],shift[15][17])}+{4'b0,abs8(shift[15][17],shift[16][17])}))+(({4'b0,abs8(shift[16][17],shift[17][17])}+{4'b0,abs8(shift[17][17],shift[18][17])})+({4'b0,abs8(shift[18][17],shift[19][17])}+{4'b0,abs8(shift[19][17],shift[20][17])}))));
reg [11:0] long8_2_0=0;
wire [11:0] long8_2_0_next=(((({4'b0,shift[1][14]}+{4'b0,shift[2][13]})+({4'b0,shift[3][12]}+{4'b0,shift[4][11]}))+(({4'b0,shift[5][10]}+{4'b0,shift[6][9]})+({4'b0,shift[7][8]}+{4'b0,shift[8][7]})))+((({4'b0,shift[9][6]}+{4'b0,shift[10][5]})+({4'b0,shift[11][4]}+{4'b0,shift[12][3]}))+(({4'b0,shift[13][2]}+{4'b0,shift[14][1]})+({4'b0,shift[15][0]}+{4'b0,shift[8][7]}))));
reg [11:0] long8_2_1=0;
wire [11:0] long8_2_1_next=(((({4'b0,shift[17][30]}+{4'b0,shift[18][29]})+({4'b0,shift[19][28]}+{4'b0,shift[20][27]}))+(({4'b0,shift[21][26]}+{4'b0,shift[22][25]})+({4'b0,shift[23][24]}+{4'b0,shift[24][23]})))+((({4'b0,shift[25][22]}+{4'b0,shift[26][21]})+({4'b0,shift[27][20]}+{4'b0,shift[28][19]}))+(({4'b0,shift[29][18]}+{4'b0,shift[30][17]})+({4'b0,shift[31][16]}+{4'b0,shift[24][23]}))));
wire [7:0] long8_flank_2=minimum(long8_2_0[4+:8],long8_2_1[4+:8]);
wire [7:0] long8_score_2=(long8_flank_2>sum_2_0[4+:8])?long8_flank_2-sum_2_0[4+:8]:0;
reg [11:0] noise_2=0;
wire [11:0] noise_2_next=(((({4'b0,abs8(shift[10][17],shift[11][16])}+{4'b0,abs8(shift[11][16],shift[12][15])})+({4'b0,abs8(shift[12][15],shift[13][14])}+{4'b0,abs8(shift[13][14],shift[14][13])}))+(({4'b0,abs8(shift[14][13],shift[15][12])}+{4'b0,abs8(shift[15][12],shift[16][11])})+({4'b0,abs8(shift[16][11],shift[17][10])}+{4'b0,abs8(shift[17][10],shift[18][9])})))+((({4'b0,abs8(shift[14][21],shift[15][20])}+{4'b0,abs8(shift[15][20],shift[16][19])})+({4'b0,abs8(shift[16][19],shift[17][18])}+{4'b0,abs8(shift[17][18],shift[18][17])}))+(({4'b0,abs8(shift[18][17],shift[19][16])}+{4'b0,abs8(shift[19][16],shift[20][15])})+({4'b0,abs8(shift[20][15],shift[21][14])}+{4'b0,abs8(shift[21][14],shift[22][13])}))));
reg [11:0] long8_3_0=0;
wire [11:0] long8_3_0_next=(((({4'b0,shift[15][30]}+{4'b0,shift[14][29]})+({4'b0,shift[13][28]}+{4'b0,shift[12][27]}))+(({4'b0,shift[11][26]}+{4'b0,shift[10][25]})+({4'b0,shift[9][24]}+{4'b0,shift[8][23]})))+((({4'b0,shift[7][22]}+{4'b0,shift[6][21]})+({4'b0,shift[5][20]}+{4'b0,shift[4][19]}))+(({4'b0,shift[3][18]}+{4'b0,shift[2][17]})+({4'b0,shift[1][16]}+{4'b0,shift[8][23]}))));
reg [11:0] long8_3_1=0;
wire [11:0] long8_3_1_next=(((({4'b0,shift[31][14]}+{4'b0,shift[30][13]})+({4'b0,shift[29][12]}+{4'b0,shift[28][11]}))+(({4'b0,shift[27][10]}+{4'b0,shift[26][9]})+({4'b0,shift[25][8]}+{4'b0,shift[24][7]})))+((({4'b0,shift[23][6]}+{4'b0,shift[22][5]})+({4'b0,shift[21][4]}+{4'b0,shift[20][3]}))+(({4'b0,shift[19][2]}+{4'b0,shift[18][1]})+({4'b0,shift[17][0]}+{4'b0,shift[24][7]}))));
wire [7:0] long8_flank_3=minimum(long8_3_0[4+:8],long8_3_1[4+:8]);
wire [7:0] long8_score_3=(long8_flank_3>sum_3_0[4+:8])?long8_flank_3-sum_3_0[4+:8]:0;
reg [11:0] noise_3=0;
wire [11:0] noise_3_next=(((({4'b0,abs8(shift[18][21],shift[17][20])}+{4'b0,abs8(shift[17][20],shift[16][19])})+({4'b0,abs8(shift[16][19],shift[15][18])}+{4'b0,abs8(shift[15][18],shift[14][17])}))+(({4'b0,abs8(shift[14][17],shift[13][16])}+{4'b0,abs8(shift[13][16],shift[12][15])})+({4'b0,abs8(shift[12][15],shift[11][14])}+{4'b0,abs8(shift[11][14],shift[10][13])})))+((({4'b0,abs8(shift[22][17],shift[21][16])}+{4'b0,abs8(shift[21][16],shift[20][15])})+({4'b0,abs8(shift[20][15],shift[19][14])}+{4'b0,abs8(shift[19][14],shift[18][13])}))+(({4'b0,abs8(shift[18][13],shift[17][12])}+{4'b0,abs8(shift[17][12],shift[16][11])})+({4'b0,abs8(shift[16][11],shift[15][10])}+{4'b0,abs8(shift[15][10],shift[14][9])}))));
wire [7:0] model_short_max=maximum(maximum(dir7_score_0,dir7_score_1),maximum(dir7_score_2,dir7_score_3));
wire [7:0] model_short_second=maximum(maximum(minimum(dir7_score_0,dir7_score_1),minimum(dir7_score_2,dir7_score_3)),minimum(maximum(dir7_score_0,dir7_score_1),maximum(dir7_score_2,dir7_score_3)));
wire [7:0] model_long_second=maximum(maximum(minimum(ridge_0,ridge_1),minimum(ridge_2,ridge_3)),minimum(maximum(ridge_0,ridge_1),maximum(ridge_2,ridge_3)));
wire [7:0] model_long8_max=maximum(maximum(long8_score_0,long8_score_1),maximum(long8_score_2,long8_score_3));
wire [1:0] model_short_dir=(dir7_score_0==model_short_max)?0:(dir7_score_1==model_short_max)?1:(dir7_score_2==model_short_max)?2:3;
wire [1:0] model_long_dir=(ridge_0==mean_max)?0:(ridge_1==mean_max)?1:(ridge_2==mean_max)?2:3;
wire [7:0] model_agree=(model_short_dir==model_long_dir)?8'hff:8'h00;
wire [7:0] model_noise=(model_short_dir==0)?noise_0[11:4]:(model_short_dir==1)?noise_1[11:4]:(model_short_dir==2)?noise_2[11:4]:noise_3[11:4];
wire [7:0] model_short_margin=model_short_max-model_short_second;
wire [7:0] model_long_margin=mean_max-model_long_second;
reg [10:0] model_background=0;
wire [7:0] model_valley=(pair_valid && shoulder>center_q)?shoulder-center_q:0;
wire [10:0] model_background_next=((({3'b0,shift[16][11]}+{3'b0,shift[16][19]})+({3'b0,shift[20][15]}+{3'b0,shift[12][15]}))+(({3'b0,shift[16][7]}+{3'b0,shift[16][23]})+({3'b0,shift[24][15]}+{3'b0,shift[8][15]})));
reg [7:0] feature_short_a0=0,feature_long_a0=0,feature_noise_a0=0,feature_noise_b0=0;
reg [7:0] feature_short_a1=0,feature_long_a1=0,feature_noise_a1=0,feature_noise_b1=0;
reg [7:0] feature_short_a2=0,feature_long_a2=0,feature_noise_a2=0,feature_noise_b2=0;
reg [7:0] feature_short_a3=0,feature_long_a3=0,feature_noise_a3=0,feature_noise_b3=0;
reg feature_valid_a=0,feature_valid_b=0;
reg [47:0] feature_basic_a=0,feature_basic_b=0;
reg [7:0] feature_short_max_b=0,feature_short_second_b=0,feature_long_second_b=0;
reg [1:0] feature_short_dir_b=0,feature_long_dir_b=0;
wire [7:0] feature_short_max_a=maximum(maximum(feature_short_a0,feature_short_a1),maximum(feature_short_a2,feature_short_a3));
wire [7:0] feature_short_second_a=maximum(maximum(minimum(feature_short_a0,feature_short_a1),minimum(feature_short_a2,feature_short_a3)),minimum(maximum(feature_short_a0,feature_short_a1),maximum(feature_short_a2,feature_short_a3)));
wire [7:0] feature_long_second_a=maximum(maximum(minimum(feature_long_a0,feature_long_a1),minimum(feature_long_a2,feature_long_a3)),minimum(maximum(feature_long_a0,feature_long_a1),maximum(feature_long_a2,feature_long_a3)));
wire [1:0] feature_short_dir_a=(feature_short_a0==feature_short_max_a)?0:(feature_short_a1==feature_short_max_a)?1:(feature_short_a2==feature_short_max_a)?2:3;
wire [1:0] feature_long_dir_a=(feature_long_a0==feature_basic_a[15:8])?0:(feature_long_a1==feature_basic_a[15:8])?1:(feature_long_a2==feature_basic_a[15:8])?2:3;
wire [7:0] feature_noise_b=(feature_short_dir_b==0)?feature_noise_b0:(feature_short_dir_b==1)?feature_noise_b1:(feature_short_dir_b==2)?feature_noise_b2:feature_noise_b3;
wire [7:0] feature_agree_b=(feature_short_dir_b==feature_long_dir_b)?8'hff:8'h00;
wire [7:0] feature_short_margin_b=feature_short_max_b-feature_short_second_b;
wire [7:0] feature_long_margin_b=feature_basic_b[15:8]-feature_long_second_b;
 always @(posedge clk)begin
  if(reset)begin x<=0;y<=0;xq<=0;yq<=0;pd<=0;pv<=0;vq<=0;score<=0;mean_score<=0;wide_line_score<=0;direction_weak<=0;pair_valid<=0;narrow_score<=0;short_score<=0;n8_valid<=0;features_hi<=0;features_valid<=0;feature_valid_a<=0;feature_valid_b<=0;end
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
   long8_0_0<=long8_0_0_next;
   long8_0_1<=long8_0_1_next;
   noise_0<=noise_0_next;
   long8_1_0<=long8_1_0_next;
   long8_1_1<=long8_1_1_next;
   noise_1<=noise_1_next;
   long8_2_0<=long8_2_0_next;
   long8_2_1<=long8_2_1_next;
   noise_2<=noise_2_next;
   long8_3_0<=long8_3_0_next;
   long8_3_1<=long8_3_1_next;
   noise_3<=noise_3_next;
   model_background<=model_background_next;
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
   feature_short_a0<=dir7_score_0;feature_long_a0<=ridge_0;feature_noise_a0<=noise_0[11:4];
   feature_noise_b0<=feature_noise_a0;
   feature_short_a1<=dir7_score_1;feature_long_a1<=ridge_1;feature_noise_a1<=noise_1[11:4];
   feature_noise_b1<=feature_noise_a1;
   feature_short_a2<=dir7_score_2;feature_long_a2<=ridge_2;feature_noise_a2<=noise_2[11:4];
   feature_noise_b2<=feature_noise_a2;
   feature_short_a3<=dir7_score_3;feature_long_a3<=ridge_3;feature_noise_a3<=noise_3[11:4];
   feature_noise_b3<=feature_noise_a3;
   feature_valid_a<=pair_valid;feature_valid_b<=feature_valid_a;features_valid<=feature_valid_b;
   feature_basic_a<={model_background[10:3],center_q,model_long8_max,wide7_max,mean_max,model_valley};
   feature_basic_b<=feature_basic_a;
   feature_short_max_b<=feature_short_max_a;feature_short_second_b<=feature_short_second_a;feature_long_second_b<=feature_long_second_a;
   feature_short_dir_b<=feature_short_dir_a;feature_long_dir_b<=feature_long_dir_a;
   features_hi<=feature_valid_b?{feature_noise_b,feature_agree_b,feature_long_margin_b,feature_short_margin_b,feature_basic_b[47:40],feature_basic_b[39:32],feature_basic_b[31:24],feature_basic_b[23:16],feature_basic_b[15:8],feature_short_max_b,feature_basic_b[7:0]}:88'd0;
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
