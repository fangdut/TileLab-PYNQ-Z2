`timescale 1ns/1ps
module tb_capture_integration;
reg pc=0,cc=0,reset=1;always #7 pc=~pc;always #5 cc=~cc;
reg [31:0] request=0;reg [23:0] rgb=0;reg de=0,vs=0;
wire [31:0] src_data,dst_data,seq,n,lo,hi,status,cfg;
wire src_valid,src_ready,src_last,dst_valid,dst_last,rstn;
system_capture_ready_reset_0 reset_bridge(.slowest_sync_clk(pc),.ext_reset_in(reset),.aux_reset_in(1'b0),.mb_debug_sys_rst(1'b0),.dcm_locked(1'b1),.peripheral_aresetn(rstn));
frame_capture #(.WIDTH(32),.HEIGHT(24)) capture(.pixel_clk(pc),.control_clk(cc),.reset(reset),.request(request),
 .rgb(rgb),.de(de),.vs(vs),.mask(1'b0),.config_word(32'h00f32407),
 .m_axis_tdata(src_data),.m_axis_tvalid(src_valid),.m_axis_tready(src_ready),.m_axis_tlast(src_last),
 .cap_seq(seq),.cap_count(n),.cap_min(lo),.cap_max(hi),.cap_status(status),.cap_config(cfg));
system_capture_fifo_0 fifo(.s_axis_aresetn(rstn),.s_axis_aclk(pc),.m_axis_aclk(cc),
 .s_axis_tdata(src_data),.s_axis_tvalid(src_valid),.s_axis_tready(src_ready),.s_axis_tlast(src_last),
 .m_axis_tdata(dst_data),.m_axis_tvalid(dst_valid),.m_axis_tready(1'b1),.m_axis_tlast(dst_last));
integer got=0;reg [31:0] expected;
always @(posedge cc)if(dst_valid)begin
 expected=((got%32)<<16)|((got/32)<<8)|32'h55;
 if(dst_data!==expected)$fatal(1,"FIFO packet data mismatch at %0d got %08x expected %08x",got,dst_data,expected);
 if(dst_last !== (got==767))$fatal(1,"TLAST wrong at %0d",got);
 got=got+1;
end
initial begin
 repeat(25)@(negedge pc);reset=0;
 repeat(220)@(negedge pc);
 if(!rstn || !src_ready)$fatal(1,"Generated reset/FIFO failed to leave reset");
 request=1;repeat(10)@(negedge pc);vs=1;repeat(3)@(negedge pc);vs=0;
 repeat(10)@(negedge pc);
 for(integer y=0;y<24;y=y+1)begin
  for(integer x=0;x<32;x=x+1)begin de=1;rgb={8'(x),8'h55,8'(y)};@(negedge pc);end
  de=0;repeat(8)@(negedge pc);
 end
 repeat(100)@(negedge pc);
 if(got!=768 || status!==32'h5 || n!=0)$fatal(1,"Incomplete integrated capture got %0d status %08x",got,status);
 $display("PASS CAPTURE INTEGRATION: generated reset polarity, async FIFO, 768 exact pixels and TLAST");$finish;
end
initial begin #1000000;$fatal(1,"Integration timeout");end
endmodule
