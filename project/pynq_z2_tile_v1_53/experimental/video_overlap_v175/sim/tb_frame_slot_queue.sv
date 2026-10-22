`timescale 1ns/1ps
module tb_frame_slot_queue;
 reg clk=0;always #5 clk=~clk;
 reg resetn=0,enable=0,ca=0,cc=0,bad=0,ia=0,idone=0;
 reg [31:0] seq=0,crc=0;
 wire cg,ig,cbusy,ibusy,ready,rc,lv,drained;
 wire [31:0] cb,ib,iseq,icrc,lb,lseq,lcrc,completed,rejected,dropped,fault;
 frame_slot_queue dut(clk,resetn,enable,ca,cc,bad,seq,crc,cg,cb,cbusy,
  ia,idone,ig,ib,iseq,icrc,ibusy,ready,rc,lb,lseq,lcrc,lv,drained,
  completed,rejected,dropped,fault);
 integer cap_slot=-1,infer_slot=-1,last_slot=-1,ready_slot=-1;
 integer cap_ticks=0,infer_ticks=0,next_seq=1;
 integer memory_frame[4],cap_frame=0,infer_frame=0,last_frame=0,ready_frame=0;
 integer good_results=0,bad_frames=0,replacements=0,simultaneous=0;
 integer disabled_capture=0,disabled_infer=0,grants=0;
 integer cycle,n,slot;
 bit reset_tested=0;
 reg [31:0] rng=32'h81234567;
 function automatic [31:0] checksum(input integer value);
  checksum=32'hc3570000^(value*32'h010101);
 endfunction
 function automatic integer index_of(input [31:0] base);
  begin
   if(base<32'h06000000||base>=32'h07000000||base[21:0])$fatal(1,"Invalid slot address %h",base);
   index_of=(base-32'h06000000)>>22;
  end
 endfunction
 task tick(input bit active);
  begin
   @(negedge clk);
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   enable=active;ca=active;ia=active&&(rng[1:0]!=0);
   cc=cap_slot>=0&&cap_ticks==0;idone=infer_slot>=0&&infer_ticks==0;
   bad=cc&&cap_frame%11==0;seq=cap_frame;crc=checksum(cap_frame);
   if(!active&&cap_slot>=0)disabled_capture++;
   if(!active&&infer_slot>=0)disabled_infer++;
   @(posedge clk);#1;
   if(cap_ticks>0)cap_ticks--;
   if(infer_ticks>0)infer_ticks--;
   if(cc&&idone)simultaneous++;
   // Independent model tracks frame identity and ownership, not free-slot choice.
   if(idone)begin
    if(infer_slot<0)$fatal(1,"Unexpected inference completion");
    last_slot=infer_slot;last_frame=infer_frame;infer_slot=-1;infer_frame=0;
    good_results++;
    if(!rc||lb!=32'h06000000+(last_slot<<22)||lseq!=last_frame||lcrc!=checksum(last_frame))
     $fatal(1,"Completed result/input identity mismatch");
   end else if(rc)$fatal(1,"Spurious result commit");
   if(ig)begin
    if(!active||infer_slot>=0||ready_slot<0)$fatal(1,"Invalid inference grant");
    slot=index_of(ib);
    if(slot!=ready_slot||iseq!=ready_frame||icrc!=checksum(ready_frame))$fatal(1,"Ready frame was not correctly consumed");
    infer_slot=slot;infer_frame=ready_frame;ready_slot=-1;ready_frame=0;
    infer_ticks=cycle<503?1:1+(rng[15:8]%97);
   end
   if(cc)begin
    if(cap_slot<0)$fatal(1,"Unexpected capture commit");
    if(bad)bad_frames++;
    else if(active)begin
     if(ready_slot>=0)replacements++;
     ready_slot=cap_slot;ready_frame=cap_frame;
    end
    cap_slot=-1;cap_frame=0;
   end
   if(!active)begin ready_slot=-1;ready_frame=0;end
   if(cg)begin
    if(!active||cap_slot>=0)$fatal(1,"Invalid capture grant");
    slot=index_of(cb);
    if(slot==infer_slot||slot==last_slot||slot==ready_slot)$fatal(1,"Capture overwrites live or preserved frame");
    cap_slot=slot;cap_frame=next_seq;next_seq++;memory_frame[slot]=cap_frame;
    cap_ticks=1+(rng[7:0]%23);grants++;
   end
   if(last_slot>=0&&memory_frame[last_slot]!=last_frame)$fatal(1,"Previous result input was overwritten");
   if(infer_slot>=0&&memory_frame[infer_slot]!=infer_frame)$fatal(1,"Inference input changed while busy");
   if(cbusy!=(cap_slot>=0)||ibusy!=(infer_slot>=0)||ready!=(ready_slot>=0)||lv!=(last_slot>=0))
    $fatal(1,"Owner state differs from independent frame model");
   if(drained!=((cap_slot<0)&&(infer_slot<0)&&(ready_slot<0)))$fatal(1,"Drain indication incorrect");
   if(completed!=good_results||rejected!=bad_frames||dropped!=replacements||fault)
    $fatal(1,"Counter/protocol mismatch completed=%d/%d rejected=%d/%d dropped=%d/%d fault=%h",completed,good_results,rejected,bad_frames,dropped,replacements,fault);
  end
 endtask
 task reset_active_system;
  begin
   @(negedge clk);resetn=0;enable=0;ca=0;cc=0;ia=0;idone=0;
   repeat(3)begin
    @(posedge clk);#1;
    if(cbusy||ibusy||ready||lv||!drained||completed||rejected||dropped||fault||cg||ig||rc)
     $fatal(1,"Reset did not clear all ownership, grants and counters");
   end
   cap_slot=-1;infer_slot=-1;last_slot=-1;ready_slot=-1;
   cap_ticks=0;infer_ticks=0;cap_frame=0;infer_frame=0;last_frame=0;ready_frame=0;
   good_results=0;bad_frames=0;replacements=0;
   for(n=0;n<4;n++)memory_frame[n]=0;
   @(negedge clk);resetn=1;reset_tested=1;
  end
 endtask
 initial begin
  for(n=0;n<4;n++)memory_frame[n]=0;
  repeat(4)@(negedge clk);resetn=1;
  for(cycle=0;cycle<20000;cycle++)begin
   tick((cycle%503)<421 && (cycle%79)!=7);
   if(cycle>=8000&&!reset_tested&&cap_slot>=0&&infer_slot>=0)reset_active_system();
  end
  repeat(150)tick(0);
  if(!drained||!lv)$fatal(1,"Disable did not drain while preserving result");
  if(!reset_tested||good_results<100||replacements<100||bad_frames<10||simultaneous==0||disabled_capture==0||disabled_infer==0)
   $fatal(1,"Insufficient concurrency coverage");
  // Simultaneous invalid responses must preserve both sticky protocol bits.
  @(negedge clk);ca=0;ia=0;cc=1;idone=1;
  @(posedge clk);#1;if(fault!=3)$fatal(1,"Lost simultaneous protocol faults");
  $display("FRAME_SLOT_QUEUE_RANDOM_DRAIN_IDENTITY_PASS cycles=20150 grants=%0d completed=%0d invalid=%0d replacements=%0d simultaneous=%0d disable_cap=%0d disable_infer=%0d",grants,good_results,bad_frames,replacements,simultaneous,disabled_capture,disabled_infer);
  $finish;
 end
 initial begin #1000000;$fatal(1,"Watchdog");end
endmodule
