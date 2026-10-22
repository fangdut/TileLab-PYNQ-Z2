// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Pixel-domain producer. Insert an async FIFO between this stream and the
// DDR writer; video pixels cannot be backpressured, so overflow invalidates
// the frame. A level handshake recovers after pixel-clock/PLL reset.
module video_roi_tokens #(
 parameter integer FRAME_WIDTH=1280,FRAME_HEIGHT=720,
 parameter integer ROI_X=280,ROI_Y=0,ROI_WIDTH=720,ROI_HEIGHT=720
)(
 input wire pixel_clk,resetn,capture_active,
 input wire [23:0] rgb,input wire de,vs,
 output logic [63:0] m_data=0,output logic [1:0] m_user=0,
 output logic m_valid=0,input wire m_ready
);
 (* ASYNC_REG="TRUE" *) logic [2:0] request_sync=0;
 logic pv=0,pd=0,half=0,bad=0;logic [15:0] x=0,y=0;
 logic [31:0] frame_counter=0,selected_seq=0,pixel_count=0,first_pixel=0,crc_state=32'hffffffff;
 localparam IDLE=0,SOF=1,PIXELS=2,VALIDATE=3,FINISH=4,DONE=5;
 logic [2:0] state=IDLE;
 wire rise_vs=vs&&!pv;
 wire roi=de&&x>=ROI_X&&x<ROI_X+ROI_WIDTH&&y>=ROI_Y&&y<ROI_Y+ROI_HEIGHT;
 wire [31:0] raw_pixel={8'h00,rgb};
 function automatic [31:0] crc32(input [31:0] start,input [31:0] value);
  reg [31:0] c;integer i;begin
   c=start^value;for(i=0;i<32;i=i+1)c=(c>>1)^({32{c[0]}}&32'hedb88320);
   crc32=c;
  end
 endfunction
 always @(posedge pixel_clk)begin
  if(!resetn)begin
   request_sync<=0;pv<=0;pd<=0;x<=0;y<=0;frame_counter<=0;selected_seq<=0;
   pixel_count<=0;half<=0;bad<=0;first_pixel<=0;crc_state<=32'hffffffff;
   state<=IDLE;m_data<=0;m_user<=0;m_valid<=0;
  end else begin
   request_sync<={request_sync[1:0],capture_active};pv<=vs;pd<=de;
   if(m_valid&&m_ready)m_valid<=0;
   if(rise_vs)begin frame_counter<=frame_counter+1;x<=0;y<=0;end
   else begin
    if(de)x<=x+1;else x<=0;
    if(pd&&!de)y<=y+1;
   end
   if((state==PIXELS||state==VALIDATE)&&pd&&!de&&x!=FRAME_WIDTH)bad<=1;
   case(state)
    IDLE:if(rise_vs&&request_sync[2])begin
     selected_seq<=frame_counter+1;pixel_count<=0;half<=0;bad<=0;crc_state<=32'hffffffff;
     m_data<={32'h0,frame_counter+1};m_user<=1;m_valid<=1;state<=SOF;
    end
    SOF:begin
     if(de)bad<=1;
     if(rise_vs)begin bad<=1;state<=FINISH;end
     else if(m_valid&&m_ready)state<=PIXELS;
    end
    PIXELS:begin
     if(!request_sync[2])bad<=1;
     if(rise_vs)begin bad<=1;state<=FINISH;end
     else if(roi)begin
      pixel_count<=pixel_count+1;crc_state<=crc32(crc_state,raw_pixel);
      if(!half)begin first_pixel<=raw_pixel;half<=1;end
      else begin
       half<=0;
       if(!m_valid||m_ready)begin m_data<={raw_pixel,first_pixel};m_user<=0;m_valid<=1;end
       else bad<=1;
      end
      if(x==ROI_X+ROI_WIDTH-1&&y==ROI_Y+ROI_HEIGHT-1)state<=VALIDATE;
     end
    end
    VALIDATE:if(rise_vs)begin
     bad<=bad||y!=FRAME_HEIGHT||pixel_count!=ROI_WIDTH*ROI_HEIGHT||half;state<=FINISH;
    end
    FINISH:if(!m_valid||m_ready)begin
     m_data<={~crc_state,selected_seq};m_user<=bad?3:2;m_valid<=1;state<=DONE;
    end
    DONE:if(!request_sync[2]&&!m_valid)state<=IDLE;
    default:state<=IDLE;
   endcase
  end
 end
endmodule
