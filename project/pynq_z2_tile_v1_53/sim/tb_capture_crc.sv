// V1.37 ABI retarget only: cfg[26]=0 preserves the legacy gate for this comparison.
`timescale 1ns/1ps
module tb_capture_crc;
 reg clk=0,control=0,reset=1;always #5 clk=~clk;always #7 control=~control;
 reg ureset=1,uframe=0;reg [15:0] ugate=0,umin=0,umax=0;reg [31:0] uarea=0,ustatus=1;
 wire udone;wire [31:0] uid,uflags,uscore;
 product_tracker unit(.clk(clk),.reset(ureset),.frame_valid(uframe),.gate_pixels(ugate),.surface_xmin(umin),.surface_xmax(umax),.candidate_count(uarea),.region_status(ustatus),.decision_valid(udone),.product_id(uid),.flags(uflags),.score(uscore));
 task decision(input integer lo,hi,area,input bit expected);
 begin @(negedge clk);umin=lo;umax=hi;uarea=area;uframe=1;@(negedge clk);uframe=0;
  if(!udone || ((uflags&8)!=0)!==expected)$fatal(1,"Complete-tile ranking failed lo=%d hi=%d area=%d flags=%x",lo,hi,area,uflags);
 end endtask
 initial begin
  repeat(6)@(negedge clk);ureset=0;ugate=500;
  decision(80,600,200,1);decision(100,1100,100,1);if(!uscore[31])$fatal(1,"Complete quality flag missing");
  decision(80,1199,500,0);decision(100,1100,90,0);decision(140,1140,100,1);
  ustatus=32'h80000001;decision(300,900,1000,0);
 end
 reg [31:0] request=0,cfg=32'h00f32407,rs=0,rstatus=0;
 reg [511:0] boxes=0;reg [255:0] areas=0;
 reg [23:0] rgb=0;reg de=0,vs=0,mask=0,ready=1;
 wire [31:0] data;wire valid,last;
 frame_capture #(.WIDTH(256),.HEIGHT(240)) dut(.pixel_clk(clk),.control_clk(control),.reset(reset),.request(request),
 .rgb(rgb),.de(de),.vs(vs),.mask(mask),.config_word(cfg),.region_boxes(boxes),.region_areas(areas),.region_seq(rs),.region_status(rstatus),
 .m_axis_tdata(data),.m_axis_tvalid(valid),.m_axis_tready(ready),.m_axis_tlast(last),.cap_seq(),.cap_count(),.cap_min(),.cap_max(),.cap_status(),.cap_config());
 integer output_file; initial output_file=$fopen("crc_packets.hex","w");
 integer got=0,nword=0,i,j,k;reg [31:0] mem[0:62000];reg held=0;reg [32:0] previous;
 always @(posedge clk)begin
  if(!reset)begin
   if(held && {last,data}!==previous)$fatal(1,"AXIS data changed during backpressure");
   held=valid && !ready;previous={last,data};
   if(valid && ready)begin
    mem[nword]=data;nword=nword+1;
    $fwrite(output_file,"%08x %01x\n",data,last);
    if(last)begin
     if(got<5 && nword!=256*240+40)$fatal(1,"Frame size %d",nword);
     if(mem[nword-40]!==32'h54465337)$fatal(1,"Trailer magic");
     if(mem[nword-38]!==got+1)$fatal(1,"Frame order");
     if(got==0 && (mem[nword-3]!=1 || !(mem[nword-2]&2)))$fatal(1,"Product start");
     // V1.5 trailer word 39 stores completeness + twice the center error.
     // This clipped, symmetric test surface has zero center error.
     if(got==1 && (!(mem[nword-2]&8) || mem[nword-1]!=0))$fatal(1,"Best frame selection");
     if(got==2 && (mem[nword-2]&8))$fatal(1,"Equal frame must not replace same center");
     if(got==4 && !(mem[nword-2]&4))$fatal(1,"Product end");
     if(got==5 && !(mem[nword-34]&32'h80000000))$fatal(1,"Dropped pixel was not invalidated");
     // V1.42: invalid frame6 must not allocate a phantom ID; reset still preserves valid serial1.
     if(got==6 && (mem[nword-3]!=2 || !(mem[nword-2]&2)))$fatal(1,"Video reset reused product ID");
     got=got+1;nword=0;
    end
   end
  end
 end
 task frame(input integer id,input bit bright,input bit crack,input bit fault);
 begin
  @(negedge clk);vs=1;de=0;repeat(4)@(negedge clk);vs=0;repeat(6)@(negedge clk);
  for(j=0;j<240;j=j+1)begin
   for(i=0;i<256;i=i+1)begin
    de=1;rgb=bright?(24'ha0a0a0|((i*731+j*613+id*98765)&24'h1f1f1f)):(24'h101010|((i*17+j*91+id*1345)&24'h0f0f0f));mask=crack && i>=100 && i<102 && j>=110 && j<130;
    ready=!(fault && j==100 && i==100);@(negedge clk);
   end
   de=0;mask=0;ready=1;repeat(16)@(negedge clk);
  end
  rs=id;rstatus=crack?1:0;boxes=crack?{448'b0,16'd129,16'd101,16'd110,16'd100}:0;areas=crack?40:0;
  repeat(49)@(negedge clk);ready=0;repeat(7)@(negedge clk);ready=1;repeat(200)@(negedge clk);
 end endtask
 initial begin
  repeat(10)@(negedge clk);reset=0;request=2;repeat(10)@(negedge clk);
  frame(1,1,0,0);frame(2,1,1,0);frame(3,1,1,0);frame(4,0,0,0);frame(5,0,0,0);frame(6,1,1,1);
  reset=1;repeat(5)@(negedge clk);reset=0;repeat(10)@(negedge clk);frame(7,1,1,0);
  if(got!=7)$fatal(1,"Missing continuous frames %d",got);
  $fclose(output_file);$display("PASS continuous SG framing, PL product ID/best-frame, AXIS backpressure invalidation");$finish;
 end
 initial begin #20000000;$fatal(1,"Timeout");end
endmodule
