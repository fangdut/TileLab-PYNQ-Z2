// V1.54 candidate: R8 valley plus directional line-mean response.
// Four opposed-neighbor dark-valley scores in a 17x17 support.
// Rejects one-sided steps; supports dark lines narrower than 16 pixels.
// This is a deterministic contrast feature, not semantic crack recognition.
module directional_ridge_valley #(parameter WIDTH=1280,HEIGHT=720,H_TOTAL=1650,R=8)(
 input wire clk,reset,input wire [7:0] gray,
 input wire [23:0] rgb,input wire de,hs,vs,
 output wire [23:0] rgb_out,output wire de_out,hs_out,vs_out,
 output reg [7:0] score=0,output reg [7:0] ridge_score=0);
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
  for(row=0;row<=N;row=row+1)if(row==0 || row==R || row==N || (row>=R-7 && row<=R+7))begin
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
 // Thirty-six 8-tap directional sums. Every operand is widened before adding.
 // Seven tangent samples plus a duplicated center; mean = sum >> 3.
 // R=8 shares the existing row RAM, and keeps the same two-register latency.
 reg [10:0] sum_0_0_0=0;
 wire [10:0] next_0_0_0=(({3'b0,shift[R+0][R+4]}+{3'b0,shift[R+0][R+3]})+({3'b0,shift[R+0][R+2]}+{3'b0,shift[R+0][R+1]}))+(({3'b0,shift[R+0][R+0]}+{3'b0,shift[R+0][R-1]})+({3'b0,shift[R+0][R-2]}+{3'b0,shift[R+0][R+1]}));
 reg [10:0] sum_0_0_1=0;
 wire [10:0] next_0_0_1=(({3'b0,shift[R-2][R+4]}+{3'b0,shift[R-2][R+3]})+({3'b0,shift[R-2][R+2]}+{3'b0,shift[R-2][R+1]}))+(({3'b0,shift[R-2][R+0]}+{3'b0,shift[R-2][R-1]})+({3'b0,shift[R-2][R-2]}+{3'b0,shift[R-2][R+1]}));
 reg [10:0] sum_0_0_2=0;
 wire [10:0] next_0_0_2=(({3'b0,shift[R+2][R+4]}+{3'b0,shift[R+2][R+3]})+({3'b0,shift[R+2][R+2]}+{3'b0,shift[R+2][R+1]}))+(({3'b0,shift[R+2][R+0]}+{3'b0,shift[R+2][R-1]})+({3'b0,shift[R+2][R-2]}+{3'b0,shift[R+2][R+1]}));
 wire [7:0] flank_0_0=minimum(sum_0_0_1[10:3],sum_0_0_2[10:3]);
 wire [7:0] response_0_0=(flank_0_0>sum_0_0_0[10:3])?flank_0_0-sum_0_0_0[10:3]:0;
 reg [10:0] sum_0_1_0=0;
 wire [10:0] next_0_1_0=(({3'b0,shift[R+0][R+2]}+{3'b0,shift[R+0][R+1]})+({3'b0,shift[R+0][R+0]}+{3'b0,shift[R+0][R-1]}))+(({3'b0,shift[R+0][R-2]}+{3'b0,shift[R+0][R-3]})+({3'b0,shift[R+0][R-4]}+{3'b0,shift[R+0][R-1]}));
 reg [10:0] sum_0_1_1=0;
 wire [10:0] next_0_1_1=(({3'b0,shift[R-2][R+2]}+{3'b0,shift[R-2][R+1]})+({3'b0,shift[R-2][R+0]}+{3'b0,shift[R-2][R-1]}))+(({3'b0,shift[R-2][R-2]}+{3'b0,shift[R-2][R-3]})+({3'b0,shift[R-2][R-4]}+{3'b0,shift[R-2][R-1]}));
 reg [10:0] sum_0_1_2=0;
 wire [10:0] next_0_1_2=(({3'b0,shift[R+2][R+2]}+{3'b0,shift[R+2][R+1]})+({3'b0,shift[R+2][R+0]}+{3'b0,shift[R+2][R-1]}))+(({3'b0,shift[R+2][R-2]}+{3'b0,shift[R+2][R-3]})+({3'b0,shift[R+2][R-4]}+{3'b0,shift[R+2][R-1]}));
 wire [7:0] flank_0_1=minimum(sum_0_1_1[10:3],sum_0_1_2[10:3]);
 wire [7:0] response_0_1=(flank_0_1>sum_0_1_0[10:3])?flank_0_1-sum_0_1_0[10:3]:0;
 reg [10:0] sum_0_2_0=0;
 wire [10:0] next_0_2_0=(({3'b0,shift[R+0][R+0]}+{3'b0,shift[R+0][R-1]})+({3'b0,shift[R+0][R-2]}+{3'b0,shift[R+0][R-3]}))+(({3'b0,shift[R+0][R-4]}+{3'b0,shift[R+0][R-5]})+({3'b0,shift[R+0][R-6]}+{3'b0,shift[R+0][R-3]}));
 reg [10:0] sum_0_2_1=0;
 wire [10:0] next_0_2_1=(({3'b0,shift[R-2][R+0]}+{3'b0,shift[R-2][R-1]})+({3'b0,shift[R-2][R-2]}+{3'b0,shift[R-2][R-3]}))+(({3'b0,shift[R-2][R-4]}+{3'b0,shift[R-2][R-5]})+({3'b0,shift[R-2][R-6]}+{3'b0,shift[R-2][R-3]}));
 reg [10:0] sum_0_2_2=0;
 wire [10:0] next_0_2_2=(({3'b0,shift[R+2][R+0]}+{3'b0,shift[R+2][R-1]})+({3'b0,shift[R+2][R-2]}+{3'b0,shift[R+2][R-3]}))+(({3'b0,shift[R+2][R-4]}+{3'b0,shift[R+2][R-5]})+({3'b0,shift[R+2][R-6]}+{3'b0,shift[R+2][R-3]}));
 wire [7:0] flank_0_2=minimum(sum_0_2_1[10:3],sum_0_2_2[10:3]);
 wire [7:0] response_0_2=(flank_0_2>sum_0_2_0[10:3])?flank_0_2-sum_0_2_0[10:3]:0;
 wire [7:0] ridge_0=minimum(response_0_0,minimum(response_0_1,response_0_2));
 reg [10:0] sum_1_0_0=0;
 wire [10:0] next_1_0_0=(({3'b0,shift[R-5][R-1]}+{3'b0,shift[R-4][R-1]})+({3'b0,shift[R-3][R-1]}+{3'b0,shift[R-2][R-1]}))+(({3'b0,shift[R-1][R-1]}+{3'b0,shift[R+0][R-1]})+({3'b0,shift[R+1][R-1]}+{3'b0,shift[R-2][R-1]}));
 reg [10:0] sum_1_0_1=0;
 wire [10:0] next_1_0_1=(({3'b0,shift[R-5][R-3]}+{3'b0,shift[R-4][R-3]})+({3'b0,shift[R-3][R-3]}+{3'b0,shift[R-2][R-3]}))+(({3'b0,shift[R-1][R-3]}+{3'b0,shift[R+0][R-3]})+({3'b0,shift[R+1][R-3]}+{3'b0,shift[R-2][R-3]}));
 reg [10:0] sum_1_0_2=0;
 wire [10:0] next_1_0_2=(({3'b0,shift[R-5][R+1]}+{3'b0,shift[R-4][R+1]})+({3'b0,shift[R-3][R+1]}+{3'b0,shift[R-2][R+1]}))+(({3'b0,shift[R-1][R+1]}+{3'b0,shift[R+0][R+1]})+({3'b0,shift[R+1][R+1]}+{3'b0,shift[R-2][R+1]}));
 wire [7:0] flank_1_0=minimum(sum_1_0_1[10:3],sum_1_0_2[10:3]);
 wire [7:0] response_1_0=(flank_1_0>sum_1_0_0[10:3])?flank_1_0-sum_1_0_0[10:3]:0;
 reg [10:0] sum_1_1_0=0;
 wire [10:0] next_1_1_0=(({3'b0,shift[R-3][R-1]}+{3'b0,shift[R-2][R-1]})+({3'b0,shift[R-1][R-1]}+{3'b0,shift[R+0][R-1]}))+(({3'b0,shift[R+1][R-1]}+{3'b0,shift[R+2][R-1]})+({3'b0,shift[R+3][R-1]}+{3'b0,shift[R+0][R-1]}));
 reg [10:0] sum_1_1_1=0;
 wire [10:0] next_1_1_1=(({3'b0,shift[R-3][R-3]}+{3'b0,shift[R-2][R-3]})+({3'b0,shift[R-1][R-3]}+{3'b0,shift[R+0][R-3]}))+(({3'b0,shift[R+1][R-3]}+{3'b0,shift[R+2][R-3]})+({3'b0,shift[R+3][R-3]}+{3'b0,shift[R+0][R-3]}));
 reg [10:0] sum_1_1_2=0;
 wire [10:0] next_1_1_2=(({3'b0,shift[R-3][R+1]}+{3'b0,shift[R-2][R+1]})+({3'b0,shift[R-1][R+1]}+{3'b0,shift[R+0][R+1]}))+(({3'b0,shift[R+1][R+1]}+{3'b0,shift[R+2][R+1]})+({3'b0,shift[R+3][R+1]}+{3'b0,shift[R+0][R+1]}));
 wire [7:0] flank_1_1=minimum(sum_1_1_1[10:3],sum_1_1_2[10:3]);
 wire [7:0] response_1_1=(flank_1_1>sum_1_1_0[10:3])?flank_1_1-sum_1_1_0[10:3]:0;
 reg [10:0] sum_1_2_0=0;
 wire [10:0] next_1_2_0=(({3'b0,shift[R-1][R-1]}+{3'b0,shift[R+0][R-1]})+({3'b0,shift[R+1][R-1]}+{3'b0,shift[R+2][R-1]}))+(({3'b0,shift[R+3][R-1]}+{3'b0,shift[R+4][R-1]})+({3'b0,shift[R+5][R-1]}+{3'b0,shift[R+2][R-1]}));
 reg [10:0] sum_1_2_1=0;
 wire [10:0] next_1_2_1=(({3'b0,shift[R-1][R-3]}+{3'b0,shift[R+0][R-3]})+({3'b0,shift[R+1][R-3]}+{3'b0,shift[R+2][R-3]}))+(({3'b0,shift[R+3][R-3]}+{3'b0,shift[R+4][R-3]})+({3'b0,shift[R+5][R-3]}+{3'b0,shift[R+2][R-3]}));
 reg [10:0] sum_1_2_2=0;
 wire [10:0] next_1_2_2=(({3'b0,shift[R-1][R+1]}+{3'b0,shift[R+0][R+1]})+({3'b0,shift[R+1][R+1]}+{3'b0,shift[R+2][R+1]}))+(({3'b0,shift[R+3][R+1]}+{3'b0,shift[R+4][R+1]})+({3'b0,shift[R+5][R+1]}+{3'b0,shift[R+2][R+1]}));
 wire [7:0] flank_1_2=minimum(sum_1_2_1[10:3],sum_1_2_2[10:3]);
 wire [7:0] response_1_2=(flank_1_2>sum_1_2_0[10:3])?flank_1_2-sum_1_2_0[10:3]:0;
 wire [7:0] ridge_1=minimum(response_1_0,minimum(response_1_1,response_1_2));
 reg [10:0] sum_2_0_0=0;
 wire [10:0] next_2_0_0=(({3'b0,shift[R-5][R+4]}+{3'b0,shift[R-4][R+3]})+({3'b0,shift[R-3][R+2]}+{3'b0,shift[R-2][R+1]}))+(({3'b0,shift[R-1][R+0]}+{3'b0,shift[R+0][R-1]})+({3'b0,shift[R+1][R-2]}+{3'b0,shift[R-2][R+1]}));
 reg [10:0] sum_2_0_1=0;
 wire [10:0] next_2_0_1=(({3'b0,shift[R-7][R+2]}+{3'b0,shift[R-6][R+1]})+({3'b0,shift[R-5][R+0]}+{3'b0,shift[R-4][R-1]}))+(({3'b0,shift[R-3][R-2]}+{3'b0,shift[R-2][R-3]})+({3'b0,shift[R-1][R-4]}+{3'b0,shift[R-4][R-1]}));
 reg [10:0] sum_2_0_2=0;
 wire [10:0] next_2_0_2=(({3'b0,shift[R-3][R+6]}+{3'b0,shift[R-2][R+5]})+({3'b0,shift[R-1][R+4]}+{3'b0,shift[R+0][R+3]}))+(({3'b0,shift[R+1][R+2]}+{3'b0,shift[R+2][R+1]})+({3'b0,shift[R+3][R+0]}+{3'b0,shift[R+0][R+3]}));
 wire [7:0] flank_2_0=minimum(sum_2_0_1[10:3],sum_2_0_2[10:3]);
 wire [7:0] response_2_0=(flank_2_0>sum_2_0_0[10:3])?flank_2_0-sum_2_0_0[10:3]:0;
 reg [10:0] sum_2_1_0=0;
 wire [10:0] next_2_1_0=(({3'b0,shift[R-3][R+2]}+{3'b0,shift[R-2][R+1]})+({3'b0,shift[R-1][R+0]}+{3'b0,shift[R+0][R-1]}))+(({3'b0,shift[R+1][R-2]}+{3'b0,shift[R+2][R-3]})+({3'b0,shift[R+3][R-4]}+{3'b0,shift[R+0][R-1]}));
 reg [10:0] sum_2_1_1=0;
 wire [10:0] next_2_1_1=(({3'b0,shift[R-5][R+0]}+{3'b0,shift[R-4][R-1]})+({3'b0,shift[R-3][R-2]}+{3'b0,shift[R-2][R-3]}))+(({3'b0,shift[R-1][R-4]}+{3'b0,shift[R+0][R-5]})+({3'b0,shift[R+1][R-6]}+{3'b0,shift[R-2][R-3]}));
 reg [10:0] sum_2_1_2=0;
 wire [10:0] next_2_1_2=(({3'b0,shift[R-1][R+4]}+{3'b0,shift[R+0][R+3]})+({3'b0,shift[R+1][R+2]}+{3'b0,shift[R+2][R+1]}))+(({3'b0,shift[R+3][R+0]}+{3'b0,shift[R+4][R-1]})+({3'b0,shift[R+5][R-2]}+{3'b0,shift[R+2][R+1]}));
 wire [7:0] flank_2_1=minimum(sum_2_1_1[10:3],sum_2_1_2[10:3]);
 wire [7:0] response_2_1=(flank_2_1>sum_2_1_0[10:3])?flank_2_1-sum_2_1_0[10:3]:0;
 reg [10:0] sum_2_2_0=0;
 wire [10:0] next_2_2_0=(({3'b0,shift[R-1][R+0]}+{3'b0,shift[R+0][R-1]})+({3'b0,shift[R+1][R-2]}+{3'b0,shift[R+2][R-3]}))+(({3'b0,shift[R+3][R-4]}+{3'b0,shift[R+4][R-5]})+({3'b0,shift[R+5][R-6]}+{3'b0,shift[R+2][R-3]}));
 reg [10:0] sum_2_2_1=0;
 wire [10:0] next_2_2_1=(({3'b0,shift[R-3][R-2]}+{3'b0,shift[R-2][R-3]})+({3'b0,shift[R-1][R-4]}+{3'b0,shift[R+0][R-5]}))+(({3'b0,shift[R+1][R-6]}+{3'b0,shift[R+2][R-7]})+({3'b0,shift[R+3][R-8]}+{3'b0,shift[R+0][R-5]}));
 reg [10:0] sum_2_2_2=0;
 wire [10:0] next_2_2_2=(({3'b0,shift[R+1][R+2]}+{3'b0,shift[R+2][R+1]})+({3'b0,shift[R+3][R+0]}+{3'b0,shift[R+4][R-1]}))+(({3'b0,shift[R+5][R-2]}+{3'b0,shift[R+6][R-3]})+({3'b0,shift[R+7][R-4]}+{3'b0,shift[R+4][R-1]}));
 wire [7:0] flank_2_2=minimum(sum_2_2_1[10:3],sum_2_2_2[10:3]);
 wire [7:0] response_2_2=(flank_2_2>sum_2_2_0[10:3])?flank_2_2-sum_2_2_0[10:3]:0;
 wire [7:0] ridge_2=minimum(response_2_0,minimum(response_2_1,response_2_2));
 reg [10:0] sum_3_0_0=0;
 wire [10:0] next_3_0_0=(({3'b0,shift[R+5][R+4]}+{3'b0,shift[R+4][R+3]})+({3'b0,shift[R+3][R+2]}+{3'b0,shift[R+2][R+1]}))+(({3'b0,shift[R+1][R+0]}+{3'b0,shift[R+0][R-1]})+({3'b0,shift[R-1][R-2]}+{3'b0,shift[R+2][R+1]}));
 reg [10:0] sum_3_0_1=0;
 wire [10:0] next_3_0_1=(({3'b0,shift[R+3][R+6]}+{3'b0,shift[R+2][R+5]})+({3'b0,shift[R+1][R+4]}+{3'b0,shift[R+0][R+3]}))+(({3'b0,shift[R-1][R+2]}+{3'b0,shift[R-2][R+1]})+({3'b0,shift[R-3][R+0]}+{3'b0,shift[R+0][R+3]}));
 reg [10:0] sum_3_0_2=0;
 wire [10:0] next_3_0_2=(({3'b0,shift[R+7][R+2]}+{3'b0,shift[R+6][R+1]})+({3'b0,shift[R+5][R+0]}+{3'b0,shift[R+4][R-1]}))+(({3'b0,shift[R+3][R-2]}+{3'b0,shift[R+2][R-3]})+({3'b0,shift[R+1][R-4]}+{3'b0,shift[R+4][R-1]}));
 wire [7:0] flank_3_0=minimum(sum_3_0_1[10:3],sum_3_0_2[10:3]);
 wire [7:0] response_3_0=(flank_3_0>sum_3_0_0[10:3])?flank_3_0-sum_3_0_0[10:3]:0;
 reg [10:0] sum_3_1_0=0;
 wire [10:0] next_3_1_0=(({3'b0,shift[R+3][R+2]}+{3'b0,shift[R+2][R+1]})+({3'b0,shift[R+1][R+0]}+{3'b0,shift[R+0][R-1]}))+(({3'b0,shift[R-1][R-2]}+{3'b0,shift[R-2][R-3]})+({3'b0,shift[R-3][R-4]}+{3'b0,shift[R+0][R-1]}));
 reg [10:0] sum_3_1_1=0;
 wire [10:0] next_3_1_1=(({3'b0,shift[R+1][R+4]}+{3'b0,shift[R+0][R+3]})+({3'b0,shift[R-1][R+2]}+{3'b0,shift[R-2][R+1]}))+(({3'b0,shift[R-3][R+0]}+{3'b0,shift[R-4][R-1]})+({3'b0,shift[R-5][R-2]}+{3'b0,shift[R-2][R+1]}));
 reg [10:0] sum_3_1_2=0;
 wire [10:0] next_3_1_2=(({3'b0,shift[R+5][R+0]}+{3'b0,shift[R+4][R-1]})+({3'b0,shift[R+3][R-2]}+{3'b0,shift[R+2][R-3]}))+(({3'b0,shift[R+1][R-4]}+{3'b0,shift[R+0][R-5]})+({3'b0,shift[R-1][R-6]}+{3'b0,shift[R+2][R-3]}));
 wire [7:0] flank_3_1=minimum(sum_3_1_1[10:3],sum_3_1_2[10:3]);
 wire [7:0] response_3_1=(flank_3_1>sum_3_1_0[10:3])?flank_3_1-sum_3_1_0[10:3]:0;
 reg [10:0] sum_3_2_0=0;
 wire [10:0] next_3_2_0=(({3'b0,shift[R+1][R+0]}+{3'b0,shift[R+0][R-1]})+({3'b0,shift[R-1][R-2]}+{3'b0,shift[R-2][R-3]}))+(({3'b0,shift[R-3][R-4]}+{3'b0,shift[R-4][R-5]})+({3'b0,shift[R-5][R-6]}+{3'b0,shift[R-2][R-3]}));
 reg [10:0] sum_3_2_1=0;
 wire [10:0] next_3_2_1=(({3'b0,shift[R-1][R+2]}+{3'b0,shift[R-2][R+1]})+({3'b0,shift[R-3][R+0]}+{3'b0,shift[R-4][R-1]}))+(({3'b0,shift[R-5][R-2]}+{3'b0,shift[R-6][R-3]})+({3'b0,shift[R-7][R-4]}+{3'b0,shift[R-4][R-1]}));
 reg [10:0] sum_3_2_2=0;
 wire [10:0] next_3_2_2=(({3'b0,shift[R+3][R-2]}+{3'b0,shift[R+2][R-3]})+({3'b0,shift[R+1][R-4]}+{3'b0,shift[R+0][R-5]}))+(({3'b0,shift[R-1][R-6]}+{3'b0,shift[R-2][R-7]})+({3'b0,shift[R-3][R-8]}+{3'b0,shift[R+0][R-5]}));
 wire [7:0] flank_3_2=minimum(sum_3_2_1[10:3],sum_3_2_2[10:3]);
 wire [7:0] response_3_2=(flank_3_2>sum_3_2_0[10:3])?flank_3_2-sum_3_2_0[10:3]:0;
 wire [7:0] ridge_3=minimum(response_3_0,minimum(response_3_1,response_3_2));
 wire [7:0] ridge_max=maximum(maximum(ridge_0,ridge_1),maximum(ridge_2,ridge_3));
 always @(posedge clk)begin
  if(reset)begin x<=0;y<=0;xq<=0;yq<=0;pd<=0;pv<=0;vq<=0;score<=0;ridge_score<=0;pair_valid<=0;end
  else begin
   pd<=de;pv<=vs;vq<=de;xq<=x;yq<=y;pq<=gray;
   if(vs && !pv)begin x<=0;y<=0;end
   else begin if(de)x<=x+1'b1;else x<=0;if(pd && !de)y<=y+1'b1;end
   sum_0_0_0<=next_0_0_0;
   sum_0_0_1<=next_0_0_1;
   sum_0_0_2<=next_0_0_2;
   sum_0_1_0<=next_0_1_0;
   sum_0_1_1<=next_0_1_1;
   sum_0_1_2<=next_0_1_2;
   sum_0_2_0<=next_0_2_0;
   sum_0_2_1<=next_0_2_1;
   sum_0_2_2<=next_0_2_2;
   sum_1_0_0<=next_1_0_0;
   sum_1_0_1<=next_1_0_1;
   sum_1_0_2<=next_1_0_2;
   sum_1_1_0<=next_1_1_0;
   sum_1_1_1<=next_1_1_1;
   sum_1_1_2<=next_1_1_2;
   sum_1_2_0<=next_1_2_0;
   sum_1_2_1<=next_1_2_1;
   sum_1_2_2<=next_1_2_2;
   sum_2_0_0<=next_2_0_0;
   sum_2_0_1<=next_2_0_1;
   sum_2_0_2<=next_2_0_2;
   sum_2_1_0<=next_2_1_0;
   sum_2_1_1<=next_2_1_1;
   sum_2_1_2<=next_2_1_2;
   sum_2_2_0<=next_2_2_0;
   sum_2_2_1<=next_2_2_1;
   sum_2_2_2<=next_2_2_2;
   sum_3_0_0<=next_3_0_0;
   sum_3_0_1<=next_3_0_1;
   sum_3_0_2<=next_3_0_2;
   sum_3_1_0<=next_3_1_0;
   sum_3_1_1<=next_3_1_1;
   sum_3_1_2<=next_3_1_2;
   sum_3_2_0<=next_3_2_0;
   sum_3_2_1<=next_3_2_1;
   sum_3_2_2<=next_3_2_2;
   pair_h<=horizontal;pair_v<=vertical;pair_d1<=diag1;pair_d2<=diag2;center_q<=center;
   pair_valid<=vq && xq>=N && yq>=N && xq<WIDTH && yq<HEIGHT;
   score<=(pair_valid && shoulder>center_q)?shoulder-center_q:0;
   ridge_score<=pair_valid?ridge_max:0;
  end
 end
 // Center is R lines + R pixels before the accepted window bottom-right.
 // Window evaluation takes one additional register cycle after RAM reads.
 wire [26:0] delayed;
 raster_delay #(.WIDTH(27),.WORDS(R*H_TOTAL+R+2)) align(
 .clk(clk),.reset(reset),.din({vs,hs,de,rgb}),.dout(delayed));
 assign {vs_out,hs_out,de_out,rgb_out}=delayed;
endmodule
