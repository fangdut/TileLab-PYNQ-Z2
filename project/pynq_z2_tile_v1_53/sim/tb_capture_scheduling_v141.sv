`timescale 1ns/1ps
// Small raster isolates scheduling boundaries. Real region latency and full
// 720p payload/CRC are separately covered by tb_capture_region_porch_fixed.
module tb_capture_scheduling_v141;
 reg clk=0,ctl=0;always #5 clk=~clk;always #7 ctl=~ctl;
 reg reset=1,vs=0,de=0,mask=0,ready=1;
 reg [31:0] request=2,cfg=0,rs=0,status=1;
 reg [23:0] rgb=0;reg [511:0] boxes=0;reg [255:0] areas=0;
 wire [31:0] data;wire valid,last;
 frame_capture #(.WIDTH(8),.HEIGHT(4)) dut(.pixel_clk(clk),.control_clk(ctl),.reset(reset),.request(request),.rgb(rgb),.de(de),.vs(vs),.mask(mask),.config_word(cfg),.region_boxes(boxes),.region_areas(areas),.region_seq(rs),.region_status(status),.m_axis_tdata(data),.m_axis_tvalid(valid),.m_axis_tready(ready),.m_axis_tlast(last),.cap_seq(),.cap_count(),.cap_min(),.cap_max(),.cap_status(),.cap_config());
 integer epoch=0,packets=0,n=0,decisions=0,stalls=0,k,fd;
 integer expected[0:63],seen[0:63];reg [31:0] packet[0:127];
 reg held=0;reg [32:0] held_word;
 function [31:0] crcword(input [31:0] crc,input [31:0] word);
  reg [31:0] c;integer byte_index,bit_index;
  begin c=crc;for(byte_index=0;byte_index<4;byte_index=byte_index+1)begin
   c=c^((word>>(byte_index*8))&255);
   for(bit_index=0;bit_index<8;bit_index=bit_index+1)c=c[0]?(c>>1)^32'hedb88320:c>>1;
  end crcword=c;end
 endfunction
 function [31:0] pixel(input integer id,input integer index);
  begin pixel={7'b0,((index%3)==0),8'(id),8'(index),8'(id^index)};end
 endfunction
 function [31:0] config_for(input integer id);begin config_for=32'h00200000|(id<<16)|(id&1?32'h04000000:0)|32'h5a07;end endfunction
 reg [31:0] pc,dc;integer id,j;
 always @(posedge clk)begin
  if(reset)begin n=0;held=0;end
  else begin
   if(held && (!valid || {last,data}!==held_word))$fatal(1,"AXIS held beat changed");
   held=valid&&!ready;held_word={last,data};if(held)stalls=stalls+1;
   if(dut.decide)decisions=decisions+1;
   if(valid&&ready)begin
    if(n>=128)$fatal(1,"packet overflow");packet[n]=data;n=n+1;
    if(last)begin
     if(n!=72)$fatal(1,"partial packet accepted words=%0d",n);
     id=packet[34];if(id<1||id>63||expected[id]==0||seen[id])$fatal(1,"unexpected/duplicate sequence %0d",id);
     seen[id]=1;pc=32'hffffffff;dc=32'hffffffff;
     for(j=0;j<32;j=j+1)begin
      if(packet[j]!==pixel(id,j))$fatal(1,"pixel mismatch seq=%0d index=%0d",id,j);
      pc=crcword(pc,packet[j]);
     end
     for(j=0;j<40;j=j+1)dc=crcword(dc,j==8?0:packet[32+j]);
     if(packet[32]!==32'h54465337||packet[33]!==~pc||packet[40]!==~dc)$fatal(1,"CRC/magic seq=%0d",id);
     if(packet[39]!==config_for(id)||packet[35]!=11)$fatal(1,"old/new config/count mixed seq=%0d",id);
     if(packet[38][31] !== (expected[id]==2) || packet[41][31] !== (expected[id]==2))$fatal(1,"invalid status seq=%0d",id);
     if(expected[id]==1 && (packet[42]!==id || packet[58]!==11))$fatal(1,"region identity seq=%0d",id);
     $fwrite(fd,"%0d,%0d,%08x,%08x,%08x\n",id,expected[id]==2,packet[39],~pc,~dc);
     packets=packets+1;n=0;
    end
   end
  end
 end
 task tick(input integer cycles);begin repeat(cycles)@(negedge clk);end endtask
 task pulse;begin epoch=epoch+1;cfg=config_for(epoch);vs=1;tick(2);vs=0;tick(2);end endtask
 task raster;integer row,col,index;reg [31:0] word;begin
  for(row=0;row<4;row=row+1)begin
   for(col=0;col<8;col=col+1)begin index=row*8+col;word=pixel(epoch,index);rgb={word[23:16],word[7:0],word[15:8]};mask=word[24];de=1;tick(1);end
   de=0;mask=0;tick(4);
  end
 end endtask
 task publish(input integer frame_number);begin rs=frame_number;boxes=frame_number;areas=11;status=1;end endtask
 task drain;begin tick(150);if(dut.state!=0||valid)$fatal(1,"did not drain");end endtask
 task good_frame;begin pulse;tick(4);expected[epoch]=1;raster;publish(epoch);drain;end endtask
 task hold_last;integer timeout;begin timeout=0;
  while(!(valid&&last))begin tick(1);timeout=timeout+1;if(timeout>200)$fatal(1,"no trailer last");end
  ready=0;tick(3);
 end endtask
 initial begin
  fd=$fopen("boundary_packets.csv","w");$fwrite(fd,"sequence,invalid,config,pixel_crc,descriptor_crc\n");
  for(k=0;k<64;k=k+1)begin expected[k]=0;seen[k]=0;end
  tick(12);reset=0;tick(12);
  // Old region result after VS: finish old config/CRC then start new raster.
  pulse;expected[1]=1;raster;pulse;expected[2]=1;tick(10);publish(1);tick(150);
  if(dut.state!=1||dut.seq!=2)$fatal(1,"pending frame not armed after old result");
  raster;publish(2);drain;
  // Held TLAST across VS, released with sufficient vertical blank remaining.
  pulse;expected[3]=1;raster;publish(3);hold_last;pulse;expected[4]=1;
  cfg=32'hdeadbeef;tick(10);ready=1;tick(5);cfg=config_for(4);
  raster;publish(4);drain;
  // Release after the first row. Later horizontal blanks MUST NOT arm frame6.
  pulse;expected[5]=1;raster;publish(5);hold_last;pulse;
  fork
   raster;
   begin tick(9);ready=1;end
  join
  publish(6);drain;if(seen[6]||dut.state!=0)$fatal(1,"mid-frame restart");
  good_frame; //7
  // Missing/wrong region at first DE: invalidate frame8, skip all of9.
  pulse;expected[8]=2;raster;rs=999;boxes=999;pulse;raster;publish(9);drain;
  good_frame; //10
  // No eligibility when disabled at VS; midblank enable cannot invent one.
  request=0;tick(10);pulse;request=2;tick(10);raster;publish(11);drain;
  good_frame; //12
  // Reset during old REGIONS plus pending VS14 must clear the start window.
  pulse;raster;pulse;tick(3);reset=1;tick(4);reset=0;tick(12);
  raster;publish(14);drain;good_frame; //15
  // Reset during metadata CRC, then normal next epoch.
  pulse;raster;publish(16);while(dut.state!=5)tick(1);
  tick(3);reset=1;tick(4);reset=0;tick(12);good_frame; //17
  // Reset while final word is held; old partial output is discarded.
  pulse;raster;publish(18);hold_last;reset=1;tick(4);reset=0;ready=1;tick(12);good_frame; //19
  // A matching region exactly on next first DE remains attributable to20,
  // but there is no time for its trailer: all of21 must be skipped.
  pulse;expected[20]=1;raster;pulse;publish(20);raster;drain;good_frame; //22
  for(k=1;k<=epoch;k=k+1)if((expected[k]!=0)!==seen[k])$fatal(1,"missing seq=%0d",k);
  if(packets!=14||stalls<30||decisions!=16)$fatal(1,"coverage packets=%0d stalls=%0d decisions=%0d",packets,stalls,decisions);
  $fclose(fd);$display("PASS V141 scheduling boundaries packets=%0d stalls=%0d decisions=%0d epochs=%0d",packets,stalls,decisions,epoch);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
