// Experimental paired-pixel arithmetic only. NOT wired into the V164 bitstream.
// Ordinary RGB={R,G,B}. The upstream must supply the matching reference pixel,
// registered current pixel and per-pixel reference edge tolerance atomically.
// normalized=clip(((current*gain_q8+128)>>8)+signed_offset,0,255).
// score=max_channel(abs(reference-normalized)); comparisons are STRICT >.
// Three registered stages; the entire pipeline stalls under output backpressure.
module reference_difference_v165(
 input wire clk,aresetn,
 input wire [23:0] s_current,s_reference,
 input wire [9:0] s_gain_r,s_gain_g,s_gain_b,
 input wire signed [11:0] s_offset_r,s_offset_g,s_offset_b,
 input wire [7:0] s_edge,s_high,s_low,
 input wire [31:0] s_side,
 input wire s_sof,s_eol,s_valid,
 output wire s_ready,
 output reg [23:0] m_normalized=0,
 output reg [7:0] m_score=0,
 output reg m_strong=0,m_weak=0,
 output reg [31:0] m_side=0,
 output reg m_sof=0,m_eol=0,m_valid=0,
 input wire m_ready
);
 wire advance=!m_valid || m_ready;
 assign s_ready=advance;
 reg v1=0,v2=0;
 reg [17:0] pr=0,pg=0,pb=0;
 reg signed [11:0] br=0,bg=0,bb=0;
 reg [23:0] reference1=0,reference2=0,normalized2=0;
 reg [7:0] edge1=0,edge2=0,high1=0,high2=0,low1=0,low2=0;
 reg [31:0] side1=0,side2=0;
 reg sof1=0,sof2=0,eol1=0,eol2=0;
 wire signed [12:0] nr=$signed({3'b0,pr[17:8]})+$signed(br);
 wire signed [12:0] ng=$signed({3'b0,pg[17:8]})+$signed(bg);
 wire signed [12:0] nb=$signed({3'b0,pb[17:8]})+$signed(bb);
 function [7:0] clip8;
  input signed [12:0] value;
  begin clip8=value<0?8'd0:value>255?8'd255:value[7:0];end
 endfunction
 wire [7:0] dr=reference2[23:16]>normalized2[23:16]?reference2[23:16]-normalized2[23:16]:normalized2[23:16]-reference2[23:16];
 wire [7:0] dg=reference2[15:8]>normalized2[15:8]?reference2[15:8]-normalized2[15:8]:normalized2[15:8]-reference2[15:8];
 wire [7:0] db=reference2[7:0]>normalized2[7:0]?reference2[7:0]-normalized2[7:0]:normalized2[7:0]-reference2[7:0];
 wire [7:0] maxrg=dr>dg?dr:dg;
 wire [7:0] residual=maxrg>db?maxrg:db;
 wire [8:0] high_threshold={1'b0,high2}+{1'b0,edge2};
 wire [8:0] low_threshold={1'b0,low2}+{2'b0,edge2[7:1]};
 always @(posedge clk)begin
  if(!aresetn)begin
   v1<=0;v2<=0;m_valid<=0;m_normalized<=0;m_score<=0;
   m_strong<=0;m_weak<=0;m_side<=0;m_sof<=0;m_eol<=0;
  end else if(advance)begin
   v1<=s_valid;v2<=v1;m_valid<=v2;
   if(s_valid)begin
    pr<=s_current[23:16]*s_gain_r+18'd128;
    pg<=s_current[15:8]*s_gain_g+18'd128;
    pb<=s_current[7:0]*s_gain_b+18'd128;
    br<=s_offset_r;bg<=s_offset_g;bb<=s_offset_b;
    reference1<=s_reference;edge1<=s_edge;high1<=s_high;low1<=s_low;
    side1<=s_side;sof1<=s_sof;eol1<=s_eol;
   end
   if(v1)begin
    normalized2<={clip8(nr),clip8(ng),clip8(nb)};reference2<=reference1;
    edge2<=edge1;high2<=high1;low2<=low1;
    side2<=side1;sof2<=sof1;eol2<=eol1;
   end
   if(v2)begin
    m_normalized<=normalized2;m_score<=residual;
    m_strong<={1'b0,residual}>high_threshold;
    m_weak<={1'b0,residual}>low_threshold;
    m_side<=side2;m_sof<=sof2;m_eol<=eol2;
   end
  end
 end
endmodule
