// Three registered stages: signed gradients; absolute L1 sum; saturated display.
// Raw magnitude is 11 bits. Display = min(|Gx|+|Gy|,255), no normalization.
module sobel3x3(input wire clk,reset,ce,in_valid,border,
 input wire [71:0] window, output reg out_valid=0,
 output reg [7:0] edge_pixel=0, output reg [10:0] magnitude=0);
 wire [7:0] a=window[71:64],b=window[63:56],c=window[55:48];
 wire [7:0] d=window[47:40],f=window[31:24];
 wire [7:0] g=window[23:16],h=window[15:8],i=window[7:0];
 reg signed [10:0] gx=0,gy=0;
 reg [10:0] sum=0;reg [1:0] valid_q=0,border_q=3;
 wire [10:0] ax=gx[10] ? -gx : gx;
 wire [10:0] ay=gy[10] ? -gy : gy;
 always @(posedge clk) begin
  if(reset) begin gx<=0;gy<=0;sum<=0;valid_q<=0;border_q<=3;
   out_valid<=0;edge_pixel<=0;magnitude<=0;
  end else if(ce) begin
   gx <= $signed({3'b0,c})+($signed({3'b0,f})<<<1)+$signed({3'b0,i})
        -$signed({3'b0,a})-($signed({3'b0,d})<<<1)-$signed({3'b0,g});
   gy <= $signed({3'b0,g})+($signed({3'b0,h})<<<1)+$signed({3'b0,i})
        -$signed({3'b0,a})-($signed({3'b0,b})<<<1)-$signed({3'b0,c});
   valid_q<={valid_q[0],in_valid};border_q<={border_q[0],border};
   sum<=ax+ay;out_valid<=valid_q[1];
   magnitude<=border_q[1]?0:sum;
   edge_pixel<=border_q[1]?0:((sum>255)?8'd255:sum[7:0]);
  end
 end
endmodule
