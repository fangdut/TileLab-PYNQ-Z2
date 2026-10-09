// Fixed raster delay including blanking. At sample n, output is input[n-WORDS].
// The synchronous read register therefore counts as WORDS+1 pipeline stages.
// No RAM reset: warm-up masks stale memory until every address was overwritten.
module raster_delay #(parameter WIDTH=29,WORDS=1650)(
 input wire clk,reset,input wire [WIDTH-1:0] din,output wire [WIDTH-1:0] dout);
 localparam AW=$clog2(WORDS);
 (* ram_style="block" *) reg [WIDTH-1:0] mem[0:WORDS-1];
 reg [AW-1:0] ptr=0;reg [AW:0] warm=0;reg good=0;
 reg [WIDTH-1:0] q;
 // Keep RAM read/write enable synchronous/constant, even during reset.
 // Pointer/warm-up reset synchronously; a full overwrite precedes visible data.
 always @(posedge clk) begin q<=mem[ptr];mem[ptr]<=din;end
 always @(posedge clk) begin
  if(reset) begin ptr<=0;warm<=0;good<=0;end
  else begin
   ptr<=(ptr==WORDS-1)?0:ptr+1'b1;
   if(warm<WORDS) warm<=warm+1'b1;
   good<=(warm>=WORDS);
  end
 end
 assign dout=good?q:{WIDTH{1'b0}};
endmodule
