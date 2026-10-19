// Central RGB feature arithmetic only; no neighborhood RAM. System alignment not yet accepted.
module color_opponent_pair(input wire [23:0] rgb,output wire [15:0] features);
wire [8:0] rg={1'b0,rgb[23:16]}+9'd256-{1'b0,rgb[15:8]};
wire [8:0] gb={1'b0,rgb[15:8]}+9'd256-{1'b0,rgb[7:0]};
assign features={gb[8:1],rg[8:1]};
endmodule
