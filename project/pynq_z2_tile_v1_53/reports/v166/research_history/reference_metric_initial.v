// Experimental metric only, not the deployed video detector.
// Nine normalized current/reference RGB pixels, row-major; center is bits119:96.
// Upstream supplies aligned windows, 5x5 reference Co/Cg ranges and edge allowance.
// All inputs/sideband must belong to the same frame, coordinate and reference.
module reference_metric_v166(
 input wire clk,aresetn,
 input wire [215:0] s_current,s_reference,
 input wire [7:0] s_span_co,s_span_cg,s_edge,s_high,s_low,
 input wire [31:0] s_side,
 input wire s_sof,s_eol,s_valid,
 output wire s_ready,
 output reg [7:0] m_score=0,
 output reg m_strong=0,m_weak=0,
 output reg [31:0] m_side=0,
 output reg m_sof=0,m_eol=0,m_valid=0,
 input wire m_ready
);
 function [7:0] yy;input [23:0] rgb;integer r,g,b;begin r=rgb[23:16];g=rgb[15:8];b=rgb[7:0];yy=(r+2*g+b+2)>>2;end endfunction
 function [7:0] co;input [23:0] rgb;integer r,b;begin r=rgb[23:16];b=rgb[7:0];co=(r-b+256)>>1;end endfunction
 function [7:0] cg;input [23:0] rgb;integer r,g,b;begin r=rgb[23:16];g=rgb[15:8];b=rgb[7:0];cg=(-r+2*g-b+512)>>2;end endfunction
 function [11:0] sumco;input [215:0] pixels;integer i;reg [11:0] total;begin total=0;for(i=0;i<9;i=i+1)total=total+co(pixels[i*24+:24]);sumco=total;end endfunction
 function [11:0] sumcg;input [215:0] pixels;integer i;reg [11:0] total;begin total=0;for(i=0;i<9;i=i+1)total=total+cg(pixels[i*24+:24]);sumcg=total;end endfunction
 function [7:0] distance;input [7:0] a,b;begin distance=a>b?a-b:b-a;end endfunction
 function [7:0] maximum;input [7:0] a,b;begin maximum=a>b?a:b;end endfunction
 function [7:0] excess;input [7:0] a,b,span;reg [7:0] d;begin d=distance(a,b);excess=d>span?d-span:0;end endfunction
 wire advance=!m_valid||m_ready;assign s_ready=advance;
 reg v1=0,v2=0;
 reg [11:0] sco=0,scg=0,rco=0,rcg=0;
 reg [7:0] cy=0,ry=0,cco=0,ccg=0,crco=0,crcg=0,spco=0,spcg=0;
 reg [7:0] edge1=0,high1=0,low1=0,score2=0,edge2=0,high2=0,low2=0;
 reg [31:0] side1=0,side2=0;reg sof1=0,eol1=0,sof2=0,eol2=0;
 wire [7:0] mean_sco=(sco+12'd4)/12'd9,mean_scg=(scg+12'd4)/12'd9;
 wire [7:0] mean_rco=(rco+12'd4)/12'd9,mean_rcg=(rcg+12'd4)/12'd9;
 wire [7:0] filtered=maximum(distance(cy,ry),maximum(distance(mean_sco,mean_rco),distance(mean_scg,mean_rcg)));
 wire [7:0] restored=maximum(excess(cco,crco,spco),excess(ccg,crcg,spcg));
 wire [8:0] high_threshold={1'b0,high2}+{1'b0,edge2};
 wire [8:0] low_threshold={1'b0,low2}+{2'b0,edge2[7:1]};
 always @(posedge clk)begin
  if(!aresetn)begin v1<=0;v2<=0;m_valid<=0;m_score<=0;m_strong<=0;m_weak<=0;m_side<=0;m_sof<=0;m_eol<=0;end
  else if(advance)begin
   v1<=s_valid;v2<=v1;m_valid<=v2;
   if(s_valid)begin
    sco<=sumco(s_current);scg<=sumcg(s_current);rco<=sumco(s_reference);rcg<=sumcg(s_reference);
    cy<=yy(s_current[119:96]);ry<=yy(s_reference[119:96]);
    cco<=co(s_current[119:96]);ccg<=cg(s_current[119:96]);crco<=co(s_reference[119:96]);crcg<=cg(s_reference[119:96]);
    spco<=s_span_co;spcg<=s_span_cg;edge1<=s_edge;high1<=s_high;low1<=s_low;
    side1<=s_side;sof1<=s_sof;eol1<=s_eol;
   end
   if(v1)begin score2<=maximum(filtered,restored);edge2<=edge1;high2<=high1;low2<=low1;side2<=side1;sof2<=sof1;eol2<=eol1;end
   if(v2)begin
    m_score<=score2;m_strong<={1'b0,score2}>high_threshold;m_weak<={1'b0,score2}>low_threshold;
    m_side<=side2;m_sof<=sof2;m_eol<=eol2;
   end
  end
 end
endmodule
