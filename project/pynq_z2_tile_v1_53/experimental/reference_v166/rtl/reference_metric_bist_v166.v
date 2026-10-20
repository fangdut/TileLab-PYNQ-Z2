// Actual-hardware arithmetic self-test. No video, DDR reference or crack claim.
// Synchronous ROMs contain the first2048 source-bound oracle vectors.
module reference_metric_bist_v166(input wire clk,resetn,restart,output wire [63:0] status);
 (* ram_style="block" *) reg [505:0] inputs[0:2047];
 (* ram_style="block" *) reg [43:0] expected[0:2047];
 initial begin $readmemh("board_input.mem",inputs);$readmemh("board_expected.mem",expected);end
 reg [505:0] stimulus=0;reg sv=0;wire sr,mv;wire [7:0] score;wire hs,hw,sof,eol;wire [31:0] side;
 reg [11:0] sent=0,received=0;reg [12:0] errors=0;reg [16:0] cycles=0;
 reg done=0,timedout=0;reg [31:0] rng=32'h16620261;reg pending=0;reg [43:0] previous=0,expected_word=0;
 wire mr=cycles[6:0]>15&&rng[0]&&!done;
 reference_metric_v166 dut(.clk(clk),.aresetn(resetn&&!restart),.s_current(stimulus[505:290]),.s_reference(stimulus[289:74]),
 .s_span_co(stimulus[73:66]),.s_span_cg(stimulus[65:58]),.s_edge(stimulus[57:50]),.s_high(stimulus[49:42]),.s_low(stimulus[41:34]),
 .s_side(stimulus[33:2]),.s_sof(stimulus[1]),.s_eol(stimulus[0]),.s_valid(sv),.s_ready(sr),
 .m_score(score),.m_strong(hs),.m_weak(hw),.m_side(side),.m_sof(sof),.m_eol(eol),.m_valid(mv),.m_ready(mr));
 assign status={16'h166b,done,timedout,(errors!=0),received,sent,errors,8'b0};
 always @(posedge clk)begin
  if(!resetn||restart)begin sent<=0;received<=0;errors<=0;cycles<=0;done<=0;timedout<=0;sv<=0;pending<=0;rng<=32'h16620261;end
  else if(!done)begin
   cycles<=cycles+1;rng<={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   if(cycles>=64&&!sv&&sent<2048)begin stimulus<=inputs[sent[10:0]];sv<=1;end
   if(sv&&sr)begin sent<=sent+1;sv<=0;end
   pending<=mv&&mr;
   if(mv&&mr)begin previous<={score,hs,hw,side,sof,eol};expected_word<=expected[received[10:0]];received<=received+1;end
   if(pending&&previous!==expected_word)errors<=errors+1;
   if(received==2048&&!pending)done<=1;
   if(cycles>=100000)begin timedout<=1;done<=1;end
  end
 end
endmodule
