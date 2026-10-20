`timescale 1ns/1ps
module tb_video_tokens;
 reg clk=0;always #5 clk=~clk;
 reg resetn=0,active=0,de=0,vs=0,blocked=0;reg [23:0] rgb=0;
 integer cycle=0,current_frame=0,pairs=0,ends=0;reg expected_bad=0;reg stalled=0;reg [63:0] held_data;reg [1:0] held_user;
 wire [63:0] data;wire [1:0] user;wire valid;wire ready=!blocked&&cycle%7!=0;
 video_roi_tokens #(.FRAME_WIDTH(12),.FRAME_HEIGHT(8),.ROI_X(4),.ROI_Y(2),.ROI_WIDTH(4),.ROI_HEIGHT(4)) dut(clk,resetn,active,rgb,de,vs,data,user,valid,ready);
 function automatic [31:0] color(input integer f,input integer x,input integer y);color=((x+f*13)<<16)|((y*17+f)<<8)|(x*y+f*7);endfunction
 function automatic [31:0] golden(input integer f);case(f)
1:golden=32'h586619f8;
3:golden=32'hf02ee6a3;
5:golden=32'h198f96d2;
 default:golden=0;endcase endfunction
 always @(posedge clk)begin
  cycle<=cycle+1;
  if(stalled&&(!valid||data!=held_data||user!=held_user))$fatal(1,"Token changed while stalled");
  stalled<=valid&&!ready;held_data<=data;held_user<=user;
  if(resetn&&valid&&ready)case(user)
   1:begin if(data[31:0]!=current_frame)$fatal(1,"SOF frame id");pairs<=0;end
   0:begin
    if(data!={color(current_frame,5+(pairs*2)%4,2+(pairs*2)/4),color(current_frame,4+(pairs*2)%4,2+(pairs*2)/4)})$fatal(1,"ROI/color/order mismatch");
    pairs<=pairs+1;
   end
   default:begin
    if((user==3)!=expected_bad||data[31:0]!=current_frame||data[63:32]!=golden(current_frame))$fatal(1,"Footer/CRC/format mismatch");
    if(!expected_bad&&pairs!=8)$fatal(1,"Missing ROI pixels");
    ends<=ends+1;
   end
  endcase
  if(cycle>10000)$fatal(1,"Video watchdog");
 end
 task pulse_vs;begin @(negedge clk);vs=1;repeat(2)@(negedge clk);vs=0;repeat(2)@(negedge clk);end endtask
 task frame(input integer f,input integer height,input bit overflow);integer x,y;begin
  current_frame=f;pulse_vs();
  for(y=0;y<height;y=y+1)begin
   if(overflow&&y==2)blocked=1;if(overflow&&y==6)blocked=0;
   for(x=0;x<12;x=x+1)begin @(negedge clk);de=1;rgb=color(f,x,y);end
   @(negedge clk);de=0;repeat(4)@(negedge clk);
  end
  blocked=0;
 end endtask
 task acknowledge;begin active=0;repeat(10)@(negedge clk);active=1;repeat(10)@(negedge clk);end endtask
 initial begin
  repeat(4)@(negedge clk);resetn=1;active=1;repeat(12)@(negedge clk);
  frame(1,8,0);pulse_vs();wait(ends==1);acknowledge();
  expected_bad=1;frame(3,7,0);pulse_vs();wait(ends==2);acknowledge();
  frame(5,8,1);pulse_vs();wait(ends==3);
  $display("PL_VIDEO_ROI_RGB_CRC_FORMAT_OVERFLOW_HANDSHAKE_PASS");$finish;
 end
endmodule
