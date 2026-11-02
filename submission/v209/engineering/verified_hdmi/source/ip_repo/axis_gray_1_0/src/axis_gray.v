// AXI4-Stream one-entry elastic stage. Input/output order is {R,G,B}.
// Y=floor((77R+150G+29B)/256), all intermediates unsigned 16-bit.
module axis_gray(input wire aclk, aresetn, mode,
 input wire [23:0] s_axis_tdata, input wire s_axis_tvalid,s_axis_tuser,s_axis_tlast,
 output wire s_axis_tready,
 output reg [23:0] m_axis_tdata, output reg m_axis_tvalid,m_axis_tuser,m_axis_tlast,
 input wire m_axis_tready);
 wire [15:0] sum = (16'd77 * s_axis_tdata[23:16]) +
                   (16'd150 * s_axis_tdata[15:8]) + (16'd29 * s_axis_tdata[7:0]);
 assign s_axis_tready = !m_axis_tvalid || m_axis_tready;
 always @(posedge aclk) begin
  if(!aresetn) begin
   m_axis_tvalid<=0; m_axis_tdata<=0; m_axis_tuser<=0; m_axis_tlast<=0;
  end else if(s_axis_tready) begin
   m_axis_tvalid<=s_axis_tvalid;
   if(s_axis_tvalid) begin
    m_axis_tdata<=mode ? {sum[15:8],sum[15:8],sum[15:8]} : s_axis_tdata;
    m_axis_tuser<=s_axis_tuser; m_axis_tlast<=s_axis_tlast;
   end
  end
 end
endmodule
