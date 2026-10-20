module tb_reference_metric_v166;
 reg clk=0;always #5 clk=~clk;
 reg resetn=0;initial begin repeat(4)@(negedge clk);resetn=1;repeat(200)@(negedge clk);resetn=0;repeat(4)@(negedge clk);resetn=1;end
 localparam N=8192;
 reg [505:0] inputs[0:N-1];reg [43:0] expected[0:N-1];
 string root,result;initial begin
  if(!$value$plusargs("ROOT=%s",root)||!$value$plusargs("RESULT=%s",result))$fatal(1,"Missing vector/result paths");
  $readmemh({root,"/input.mem"},inputs);$readmemh({root,"/expected.mem"},expected);
 end
 reg [505:0] stimulus=0;reg sv=0,mr=0;wire sr,mv;wire [7:0] score;wire hit_strong,hit_weak,sof,eol;wire [31:0] side;
 reference_metric_v166 dut(
 .clk(clk),.aresetn(resetn),.s_current(stimulus[505:290]),.s_reference(stimulus[289:74]),
 .s_span_co(stimulus[73:66]),.s_span_cg(stimulus[65:58]),
 .s_edge(stimulus[57:50]),.s_high(stimulus[49:42]),.s_low(stimulus[41:34]),.s_side(stimulus[33:2]),.s_sof(stimulus[1]),.s_eol(stimulus[0]),
 .s_valid(sv),.s_ready(sr),.m_score(score),.m_strong(hit_strong),.m_weak(hit_weak),.m_side(side),.m_sof(sof),.m_eol(eol),.m_valid(mv),.m_ready(mr));
 wire [43:0] observed={score,hit_strong,hit_weak,side,sof,eol};
 integer sent=0,received=0,cycles=0,fd;reg hold_input=0,held_output=0;reg [43:0] prior=0;reg [31:0] rng=32'h16520261;
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
     fd=$fopen(result,"w");$fdisplay(fd,"PASS 8192 exact paired RGB windows/chroma spans/tolerance/threshold packets; bubbles, backpressure, sideband and reset during traffic");$fclose(fd);$finish;
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
