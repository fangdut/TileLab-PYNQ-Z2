`timescale 1ns/1ps
module tb_overlap_scheduler;
 reg clk=0;always #5 clk=~clk;
 reg resetn=0,enable=0,commit=0,invalid=0;
 reg [31:0] seq=0,crc=0;
 wire active,owner,publish,start_pulse;
 wire [31:0] cap_base,last_base,completed,rejected,last_seq,last_crc,dropped,fault;
 wire [31:0] awaddr,wdata,araddr;wire [2:0] awprot,arprot;wire [3:0] strb;
 wire awvalid,wvalid,bready,arvalid,rready;
 reg awready=0,wready=0,bvalid=0,arready=0,rvalid=0;
 reg [1:0] bresp=0,rresp=0;reg [31:0] rdata=0;
 reg result_done=0,result_error=0;
 pl_frame_scheduler_overlap #(.POLL_CYCLES(3),.REARM_CYCLES(3)) dut(
  clk,resetn,enable,commit,invalid,seq,crc,active,owner,cap_base,last_base,publish,start_pulse,
  completed,rejected,last_seq,last_crc,dropped,fault,awaddr,awprot,awvalid,awready,
  wdata,strb,wvalid,wready,bresp,bvalid,bready,araddr,arprot,arvalid,arready,rdata,rresp,rvalid,rready,result_done,result_error);
 integer cycle=0,cap_ticks=-1,frame=0,cap_frame=0,slot;
 integer memory_frame[4],pointer=0,pointers=0,starts=0,remaining=0,latch_ticks=0;
 integer input_frame=0,input_slot=-1,seen=0,overlap_cycles=0;
 reg previous_active=0,captured=0,got_aw=0,got_w=0,hls_busy=0,hls_done=0,await_result=0;
 reg [31:0] saved_aw=0,saved_w=0,held_awaddr=0,held_wdata=0;
 reg hold_aw=0,hold_w=0,inject_write=0,inject_read=0,inject_result=0;
 function automatic [31:0] checksum(input integer f);checksum=32'h51a70000^f;endfunction
 // Source writes frame identity into the selected DDR slot. It is independent
 // of the HLS latency and may finish several frames during one inference.
 always @(negedge clk)begin
  commit=0;invalid=0;
  if(!resetn)begin previous_active=0;cap_ticks=-1;captured=0;frame=0;seen=0;end
  else begin
   if(active&&!previous_active)begin
    slot=(cap_base-32'h06000000)>>22;
    if(slot<0||slot>3||cap_base[21:0])$fatal(1,"Bad capture pointer");
    if((hls_busy||await_result)&&slot==input_slot)$fatal(1,"Capture overwrites active inference");
    if(completed&&cap_base==last_base)$fatal(1,"Capture overwrites previous result input");
    frame++;cap_frame=frame;memory_frame[slot]=frame;cap_ticks=6+(frame%7);captured=0;
   end
   if(cap_ticks>0)cap_ticks--;
   else if(active&&!captured&&cap_ticks==0)begin
    seq=cap_frame;crc=checksum(cap_frame);invalid=cap_frame%9==0;commit=1;captured=1;
   end
   previous_active=active;
   if(completed!=seen)begin
    if(last_seq!=input_frame||last_crc!=checksum(input_frame)||last_base!=32'h06000000+(input_slot<<22))
     $fatal(1,"Published result is paired with wrong captured input");
    seen=completed;
   end
  end
 end
 always @(posedge clk)begin
  cycle<=cycle+1;result_done<=0;result_error<=0;
  awready<=cycle%5==0;wready<=cycle%7==0;arready<=cycle%3==0;
  if(!resetn)begin
   got_aw<=0;got_w<=0;bvalid<=0;rvalid<=0;bresp<=0;rresp<=0;
   pointer<=0;pointers<=0;starts<=0;remaining<=0;latch_ticks<=0;
   hls_busy<=0;hls_done<=0;await_result<=0;hold_aw<=0;hold_w<=0;
   input_frame<=0;input_slot<=-1;overlap_cycles<=0;
  end else begin
   if(hold_aw&&(!awvalid||awaddr!=held_awaddr))$fatal(1,"AW payload changed under backpressure");
   if(hold_w&&(!wvalid||wdata!=held_wdata))$fatal(1,"W payload changed under backpressure");
   if(awvalid&&awready)begin saved_aw<=awaddr;got_aw<=1;end
   if(wvalid&&wready)begin saved_w<=wdata;got_w<=1;end
   if(got_aw&&got_w&&!bvalid)begin
    got_aw<=0;got_w<=0;bvalid<=1;bresp<=inject_write?2:0;
    if(!inject_write)begin
     if(saved_aw==32'h43c10028)begin
      if(hls_busy||await_result)$fatal(1,"Pointer changed while engine/result is live");
      pointer<=saved_w;pointers<=pointers+1;
     end else if(saved_aw==32'h43c10000&&saved_w==1)begin
      if(hls_busy||await_result||pointers!=starts+1)$fatal(1,"Start not preceded by exactly one pointer write");
      slot=(pointer-32'h06000000)>>22;
      if(slot<0||slot>3||pointer[21:0]||memory_frame[slot]%9==0)$fatal(1,"Invalid inference input slot/frame");
      input_frame<=memory_frame[slot];input_slot<=slot;starts<=starts+1;
      hls_busy<=1;hls_done<=0;remaining<=55+(starts%17);
     end else $fatal(1,"Unexpected AXI write");
    end
   end
   if(bvalid&&bready)bvalid<=0;
   if(remaining>0)begin
    remaining<=remaining-1;
    if(remaining==1)begin hls_busy<=0;hls_done<=1;await_result<=1;end
   end
   if(arvalid&&arready)begin rvalid<=1;rdata<=hls_done?2:0;rresp<=inject_read?2:0;end
   if(rvalid&&rready)begin rvalid<=0;if(rdata[1])hls_done<=0;end
   if(publish)begin
    if(hls_busy||!await_result)$fatal(1,"Result latch started before HLS completed");
    latch_ticks<=11;
   end else if(latch_ticks>0)begin
    latch_ticks<=latch_ticks-1;
    if(latch_ticks==1)begin result_done<=1;result_error<=inject_result;await_result<=0;end
   end
   if(active&&hls_busy)overlap_cycles<=overlap_cycles+1;
   hold_aw<=awvalid&&!awready;held_awaddr<=awaddr;
   hold_w<=wvalid&&!wready;held_wdata<=wdata;
  end
  if(cycle>30000)$fatal(1,"Watchdog");
 end
 task restart;
  begin
   @(negedge clk);enable=0;resetn=0;
   repeat(4)@(negedge clk);resetn=1;enable=1;
  end
 endtask
 integer old_starts;
 initial begin
  for(integer n=0;n<4;n++)memory_frame[n]=0;
  restart();wait(completed>=25);wait(active&&hls_busy);
  @(negedge clk);enable=0;wait(!owner);
  if(overlap_cycles<300||dropped==0||rejected==0||fault)$fatal(1,"No valid concurrent acquisition evidence");
  old_starts=starts;repeat(100)@(negedge clk);
  if(starts!=old_starts)$fatal(1,"New inference started after drain");
  enable=1;wait(completed>=35);
  inject_write=1;wait(fault[0]);old_starts=starts;
  repeat(100)@(negedge clk);if(starts!=old_starts)$fatal(1,"Write fault did not stop starts");
  inject_write=0;inject_read=1;restart();wait(fault[1]);
  inject_read=0;inject_result=1;restart();wait(fault[2]);
  $display("OVERLAP_SCHEDULER_POINTER_AXI_STALL_DRAIN_IDENTITY_FAULTS_PASS");$finish;
 end
endmodule
