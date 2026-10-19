module tb_reference_difference_v165;
 reg clk=0;always #5 clk=~clk;
 reg resetn=0;initial begin repeat(4)@(negedge clk);resetn=1;repeat(200)@(negedge clk);resetn=0;repeat(4)@(negedge clk);resetn=1;end
 localparam N=8192;
 reg [171:0] inputs[0:N-1];reg [67:0] expected[0:N-1];
 string root,result;initial begin
  if(!$value$plusargs("ROOT=%s",root)||!$value$plusargs("RESULT=%s",result))$fatal(1,"Missing vector/result paths");
  $readmemh({root,"/input.mem"},inputs);$readmemh({root,"/expected.mem"},expected);
 end
 reg [171:0] stimulus=0;reg sv=0,mr=0;wire sr,mv;wire [23:0] normalized;wire [7:0] score;wire hit_strong,hit_weak,sof,eol;wire [31:0] side;
 reference_difference_v165 dut(
 .clk(clk),.aresetn(resetn),.s_current(stimulus[171:148]),.s_reference(stimulus[147:124]),
 .s_gain_r(stimulus[123:114]),.s_gain_g(stimulus[113:104]),.s_gain_b(stimulus[103:94]),
 .s_offset_r(stimulus[93:82]),.s_offset_g(stimulus[81:70]),.s_offset_b(stimulus[69:58]),
 .s_edge(stimulus[57:50]),.s_high(stimulus[49:42]),.s_low(stimulus[41:34]),.s_side(stimulus[33:2]),.s_sof(stimulus[1]),.s_eol(stimulus[0]),
 .s_valid(sv),.s_ready(sr),.m_normalized(normalized),.m_score(score),.m_strong(hit_strong),.m_weak(hit_weak),.m_side(side),.m_sof(sof),.m_eol(eol),.m_valid(mv),.m_ready(mr));
 wire [67:0] observed={normalized,score,hit_strong,hit_weak,side,sof,eol};
 integer sent=0,received=0,cycles=0,fd;reg hold_input=0,held_output=0;reg [67:0] prior=0;reg [31:0] rng=32'h16520261;
 always @(posedge clk)begin
  if(!resetn)begin sent<=0;received<=0;cycles<=0;hold_input<=0;held_output<=0;end
  else begin
   cycles<=cycles+1;hold_input<=sv&&!sr;held_output<=mv&&!mr;prior<=observed;
   if(held_output && (!mv || observed!==prior))$fatal(1,"Output changed under backpressure");
   if(sv&&sr)sent<=sent+1;
   if(mv&&mr)begin
    if(received>=N || observed!==expected[received])$fatal(1,"Mismatch %0d actual=%h expected=%h",received,observed,expected[received]);
    received<=received+1;
    if(received==N-1)begin
     fd=$fopen(result,"w");$fdisplay(fd,"PASS 8192 exact paired RGB/gain/signed-offset/tolerance/threshold packets; bubbles, backpressure, sideband and reset during traffic");$fclose(fd);$finish;
    end
   end
   if(cycles>100000)$fatal(1,"Watchdog");
  end
 end
 always @(negedge clk)begin
  rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
  if(!resetn)begin sv=0;mr=0;end
  else begin
   mr=(cycles%73>15)&&rng[0];
   if(!hold_input)begin sv=(sent<N)&&rng[3];if(sent<N)stimulus=inputs[sent];end
  end
 end
endmodule
