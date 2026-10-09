// Fixed 3x3 Gaussian: [1 2 1; 2 4 2; 1 2 1] / 16, floor.
// Three registered stages match sobel3x3. All stages freeze when CE=0.
// First/last image row/column is black, matching the shared window contract.
module gaussian3x3(input wire clk,reset,ce,in_valid,border,
 input wire [71:0] window,output reg out_valid=0,
 output reg [7:0] pixel_out=0);
 wire [7:0] a=window[71:64],b=window[63:56],c=window[55:48];
 wire [7:0] d=window[47:40],e=window[39:32],f=window[31:24];
 wire [7:0] g=window[23:16],h=window[15:8],i=window[7:0];
 reg [9:0] row0=0,row1=0,row2=0;
 reg [11:0] sum=0;
 reg [1:0] valid_q=0,border_q=3;
 always @(posedge clk) begin
  if(reset) begin
   row0<=0;row1<=0;row2<=0;sum<=0;valid_q<=0;border_q<=3;
   out_valid<=0;pixel_out<=0;
  end else if(ce) begin
   row0<={2'b0,a}+{1'b0,b,1'b0}+{2'b0,c};
   row1<={2'b0,d}+{1'b0,e,1'b0}+{2'b0,f};
   row2<={2'b0,g}+{1'b0,h,1'b0}+{2'b0,i};
   sum<={2'b0,row0}+{1'b0,row1,1'b0}+{2'b0,row2};
   valid_q<={valid_q[0],in_valid};border_q<={border_q[0],border};
   out_valid<=valid_q[1];pixel_out<=border_q[1]?8'b0:sum[11:4];
  end
 end
endmodule
