`timescale 1ns/1ps
// Real SG capture + tracker. Two truncated bright-tile observations before
// its gate rows must complete invalid packets without splitting product1.
module tb_tracker_capture_invalid;
 reg clk=0,ctl=0;always #5 clk=~clk;always #7 ctl=~ctl;
 reg reset=1,vs=0,de=0,mask=0;reg [23:0] rgb=0;reg [31:0] rs=0,st=0;
 wire [31:0] data;wire valid,last;
 frame_capture #(.WIDTH(256),.HEIGHT(240)) dut(.pixel_clk(clk),.control_clk(ctl),.reset(reset),.request(32'd2),.rgb(rgb),.de(de),.vs(vs),.mask(mask),.config_word(32'h00f32407),.region_boxes(512'b0),.region_areas(256'b0),.region_seq(rs),.region_status(st),.m_axis_tdata(data),.m_axis_tvalid(valid),.m_axis_tready(1'b1),.m_axis_tlast(last),.cap_seq(),.cap_count(),.cap_min(),.cap_max(),.cap_status(),.cap_config());
 integer epoch=0,n=0,packets=0,decisions=0,fd,k,actual_id,actual_flags;
 reg [31:0] memory[0:61500],crc,dc;
 function [31:0] crcword(input [31:0] c0,input [31:0] word);
  reg [31:0] c;integer byte_index,bit_index;
  begin c=c0;for(byte_index=0;byte_index<4;byte_index=byte_index+1)begin
   c=c^((word>>(byte_index*8))&255);for(bit_index=0;bit_index<8;bit_index=bit_index+1)c=c[0]?(c>>1)^32'hedb88320:c>>1;
  end crcword=c;end
 endfunction
 always @(posedge clk)begin
  if(!reset)begin
   if(dut.decide)decisions=decisions+1;
   if(valid)begin
    memory[n]=data;n=n+1;if(n>61480)$fatal(1,"packet overflow");
    if(last)begin
     packets=packets+1;
     if(memory[n-38]!=packets || memory[n-40]!==32'h54465337)$fatal(1,"sequence/magic mismatch");
     if(n!=((packets==2||packets==3)?2560:61440)+40)$fatal(1,"packet length");
     if(memory[n-34][31] !== (packets==2||packets==3) || memory[n-31][31] !== (packets==2||packets==3))$fatal(1,"partial frame not explicitly invalid");
     crc=32'hffffffff;dc=32'hffffffff;
     for(k=0;k<n-40;k=k+1)crc=crcword(crc,memory[k]);
     for(k=0;k<40;k=k+1)dc=crcword(dc,k==8?0:memory[n-40+k]);
     if(memory[n-39]!==~crc||memory[n-32]!==~dc)$fatal(1,"pixel/descriptor CRC mismatch");
     actual_id=memory[n-3];actual_flags=memory[n-2];
     if(actual_id!=(packets==7?2:1))$fatal(1,"invalid observations split physical tile packet=%0d id=%0d",packets,actual_id);
     case(packets)
      1,7:if(actual_flags!=27)$fatal(1,"valid tile did not start/update");
      2,3,5:if(actual_flags!=0)$fatal(1,"invalid or first-clear lifecycle event");
      4:if(actual_flags!=17)$fatal(1,"recovered tile must keep ID and best frame");
      6:if(actual_flags!=4)$fatal(1,"two valid clear frames must end product");
     endcase
     $fwrite(fd,"%0d,%0d,%0d,%08x,%08x,%08x,%08x\n",packets,n,actual_id,actual_flags,memory[n-34],~crc,~dc);n=0;
    end
   end
  end
 end
 task tick(input integer count);begin repeat(count)@(negedge clk);end endtask
 task begin_frame;begin epoch=epoch+1;vs=1;tick(2);vs=0;tick(150);end endtask
 task raster(input integer rows,input reg bright);integer y,x;begin
  for(y=0;y<rows;y=y+1)begin
   for(x=0;x<256;x=x+1)begin de=1;rgb=bright?24'ha0a0a0:24'h101010;mask=bright&&x>=100&&x<102&&y>=110&&y<130;tick(1);end
   de=0;mask=0;tick(16);
  end
 end endtask
 task result_region;begin rs=epoch;st=1;end endtask
 initial begin
  fd=$fopen("packets.csv","w");$fwrite(fd,"seq,words,product_id,product_flags,capture_status,pixel_crc,descriptor_crc\n");
  tick(12);reset=0;tick(12);
  begin_frame;raster(240,1);result_region;tick(150);
  begin_frame;raster(10,1);result_region;
  begin_frame;raster(10,1);result_region;
  begin_frame;raster(240,1);result_region;tick(150);
  begin_frame;raster(240,0);rs=epoch;st=0;tick(150);
  begin_frame;raster(240,0);rs=epoch;st=0;tick(150);
  begin_frame;raster(240,1);result_region;tick(150);
  if(packets!=7||decisions!=7||n!=0)$fatal(1,"capture deadlock/coverage packets=%0d decisions=%0d",packets,decisions);
  $fclose(fd);$display("PASS V142 INTEGRATED:7 complete decisions/packets,2 explicit truncated invalid,one tile ID retained,CRC14");$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
