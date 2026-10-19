`timescale 1ns/1ps
module tb_selected_v156;
 parameter FRAMES=160;
 parameter W=96,H=80,HT=144,VT=109,TOP=24;
 // Each added registered stage contributes HT+4 sampled clocks when cascaded.
 localparam LAG=25*HT+59+11;
 reg clk=0,cc=0;always #5 clk=~clk;always #3.5 cc=~cc;
 reg reset=1,de=0,hs=0,vs=0;reg [23:0] rgb=0;reg [31:0] cfg=0,rmin=0,rmax=0;
 wire [23:0] out;wire od,oh,ov,ok,pr,wv;wire [2:0] mode;wire [31:0] fc,fp,act;wire [15:0] fl,lp,ox,oy;
 video_bypass #(.WIDTH(W),.HEIGHT(H),.H_TOTAL(HT)) dut(
 .pixel_clk(clk),.control_clk(cc),.reset(reset),.config_request(cfg),.roi_min_request(rmin),.roi_max_request(rmax),
 .rgb_in(rgb),.de_in(de),.hs_in(hs),.vs_in(vs),.rgb_out(out),.de_out(od),.hs_out(oh),.vs_out(ov),
 .frame_count(fc),.frame_pixels(fp),.frame_lines(fl),.line_pixels(lp),.format_ok(ok),.mode_active(mode),.pixel_reset(pr),.window_valid(wv),
 .out_x(ox),.out_y(oy),.config_active(act),.candidate_count_ref(sn),.bbox_min_ref(slo),.bbox_max_ref(shi),.snapshot_seq_ref(sseq),.snapshot_config_ref(scfg),.snapshot_status_ref(sstatus),
 .brightness_count_ref(bn),.brightness_sum_ref(bs),.brightness_seq_ref(bseq),.brightness_config_ref(bcfg),.brightness_min_ref(bmin),.brightness_max_ref(bmax),.mask_crc_ref(scrc));
 wire [31:0] sn,slo,shi,sseq,scfg,sstatus,bn,bs,bseq,bcfg,bmin,bmax,scrc;
 reg [31:0] gold_bn[0:FRAMES],gold_bs[0:FRAMES];integer brightness_checked=0;
 always @(posedge cc)begin
  #1;
  if(bseq>brightness_checked)begin
   if(bseq!=brightness_checked+1)$fatal(1,"brightness sequence gap");
   if({bn,bs,bcfg,bmin,bmax}!=={gold_bn[brightness_checked],gold_bs[brightness_checked],gold_cfg[brightness_checked],32'(((H/4)<<16)|(W/5)),32'(((3*H/4)<<16)|(3*W/5))})
    $fatal(1,"brightness frame=%d n=%d sum=%d expected=%d/%d cfg=%h expectedcfg=%h",brightness_checked,bn,bs,gold_bn[brightness_checked],gold_bs[brightness_checked],bcfg,gold_cfg[brightness_checked]);
   brightness_checked++;
  end
 end
 reg [31:0] gold_status[0:FRAMES];
 reg [31:0] gold_crc[0:FRAMES],gold_n[0:FRAMES],gold_lo[0:FRAMES],gold_hi[0:FRAMES],gold_cfg[0:FRAMES];integer stats_checked=0;
 always @(posedge cc)begin
  #1;
  if(sseq>stats_checked)begin
   if(sseq!=stats_checked+1)$fatal(1,"lost stats sequence");
   if({sn,slo,shi,scfg,sstatus}!=={gold_n[stats_checked],gold_lo[stats_checked],gold_hi[stats_checked],gold_cfg[stats_checked],gold_status[stats_checked]})
    $fatal(1,"integrated stats frame=%0d count=%d expected=%d lo=%h hi=%h cfg=%h expectedcfg=%h",stats_checked,sn,gold_n[stats_checked],slo,shi,scfg,gold_cfg[stats_checked]);
   if(scrc!==gold_crc[stats_checked])$fatal(1,"CRC frame=%d got=%h expected=%h",stats_checked,scrc,gold_crc[stats_checked]);
   stats_checked++;
  end
 end
 reg [23:0] input_image[0:W*H-1],gold[0:W*H-1];reg [31:0] configs[0:FRAMES-1];
 reg [26:0] q[0:LAG-1];integer ptr=0,count=0;string root,name,result;integer dx=0,dy=0,proof;reg pde=0,pvs=0;
 task tick(input bit d,h,v,input [23:0] c,g);
  @(negedge clk);de=d;hs=h;vs=v;rgb=c;
  @(posedge clk);#1;
  if({ov,oh,od}!==q[ptr][26:24])$fatal(1,"sync mismatch t=%t got=%b exp=%b pr=%b core=%b%b%b p1=%b%b%b p2=%b%b%b warm=%d",$time,{ov,oh,od},q[ptr][26:24],pr,dut.vs,dut.hs,dut.de,dut.v1,dut.h1,dut.d1,dut.v2,dut.h2,dut.d2,dut.pass2.align.warm);
  if(od)begin
   if(out!==q[ptr][23:0])$fatal(1,"pixel n=%0d x=%0d y=%0d got=%h exp=%h mode=%0d",count,ox,oy,out,q[ptr][23:0],mode);
   count++;
  end
  q[ptr]={v,h,d,g};ptr=(ptr+1)%LAG;
 endtask
 initial begin
  if(!$value$plusargs("ROOT=%s",root))$fatal(1,"missing ROOT");
  if(!$value$plusargs("RESULT=%s",result))$fatal(1,"missing RESULT");
  $readmemh({root,"/brightness_count.mem"},gold_bn);$readmemh({root,"/brightness_total.mem"},gold_bs);
  $readmemh({root,"/stats_crc.mem"},gold_crc);$readmemh({root,"/stats_status.mem"},gold_status);
  $readmemh({root,"/stats_count.mem"},gold_n);$readmemh({root,"/stats_lo.mem"},gold_lo);$readmemh({root,"/stats_hi.mem"},gold_hi);$readmemh({root,"/stats_config.mem"},gold_cfg);
  $readmemh({root,"/input.mem"},input_image);$readmemh({root,"/config.mem"},configs);
  for(integer i=0;i<LAG;i++)q[i]=0;
  // Hold reset beyond Xilinx glbl's initial 100ns GSR interval.
  repeat(30)@(negedge clk);reset=0;repeat(15)@(negedge clk);
  rmin=((H/4)<<16)|(W/5);rmax=((3*H/4)<<16)|(3*W/5);
  for(integer f=0;f<FRAMES;f++)begin
   if(f%32==0)$display("PROGRESS selected frame %0d/%0d",f,FRAMES);
   cfg=configs[f];name=$sformatf("%s/expected%0d.mem",root,f);$readmemh(name,gold);
   for(integer ry=0;ry<VT;ry++)for(integer xx=0;xx<HT;xx++)
    tick(ry>=TOP && ry<TOP+H && xx<W,xx>=W+10 && xx<W+20,ry<3,
     (ry>=TOP && ry<TOP+H && xx<W)?input_image[(ry-TOP)*W+xx]:0,
     (ry>=TOP && ry<TOP+H && xx<W)?gold[(ry-TOP)*W+xx]:0);
  end
  for(integer i=0;i<LAG+200;i++)tick(0,0,i<3*HT,0,0);
  if(count!=FRAMES*W*H)$fatal(1,"count %0d",count);
  if(W==32)begin
   reset=1;repeat(20)@(negedge clk);
   if(od || fc || ok)$fatal(1,"reset did not mask output/statistics");
   for(integer i=0;i<LAG;i++)q[i]=0;ptr=0;
   $readmemh({root,"/recovery_input.mem"},input_image);$readmemh({root,"/recovery_expected.mem"},gold);
   cfg=32'h80006406;reset=0;repeat(20)@(negedge clk);
   for(integer ry=0;ry<VT;ry++)for(integer xx=0;xx<HT;xx++)
    tick(ry>=TOP && ry<TOP+H && xx<W,xx>=W+10 && xx<W+20,ry<3,
     (ry>=TOP && ry<TOP+H && xx<W)?input_image[(ry-TOP)*W+xx]:0,
     (ry>=TOP && ry<TOP+H && xx<W)?gold[(ry-TOP)*W+xx]:0);
   for(integer i=0;i<LAG+200;i++)tick(0,0,i<3*HT,0,0);
   if(count!=(FRAMES+1)*W*H)$fatal(1,"recovery count");
   $display("PASS RESET: changed image after reset, no stale line/raster memory pixels");
  end
  if(stats_checked!=(W==32?FRAMES+1:FRAMES))$fatal(1,"stats missing %d",stats_checked);
  if(brightness_checked!=(W==32?FRAMES+1:FRAMES))$fatal(1,"missing brightness snapshots");
  $display("PASS BRIGHTNESS INTEGRATED: %0d complete frames ROI count sum config coordinates exact",brightness_checked);
  $display("PASS FRAME CRC: %0d complete frames match independent zlib",stats_checked);
  $display("PASS INTEGRATED STATS: %0d complete frames count bbox config and sequence exact",stats_checked);
  proof=$fopen(result,"w");if(!proof)$fatal(1,"Cannot write success proof");
  $fdisplay(proof,"PASS %0d pixels, %0d frames, masks, RGB, sync, config, stats, brightness and CRC",count,stats_checked);$fclose(proof);
  $display("PASS DETECTION: %0d exact pixels, 128 configurations: legacy and fixed support profiles, two/four/eight passes, colored RBG pixels, threshold extremes, ROI and per-frame commits, sync lag %0d",count,LAG);$finish;
 end
 initial begin #450000000;$fatal(1,"timeout");end
endmodule


