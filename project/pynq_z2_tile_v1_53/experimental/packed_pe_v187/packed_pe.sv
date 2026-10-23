// Experimental arithmetic unit only; not connected to the TileLab detector.
// Three enabled-clock stages. Both modes share the same signed 25 x 18 multiply.
module packed_pe(
    input wire clk, reset, ce, valid_in, square_mode,
    input wire signed [7:0] activation, weight0, weight1,
    input wire signed [16:0] difference,
    output reg valid_out, square_out,
    output reg signed [15:0] product0, product1,
    output reg [33:0] squared
);
    reg signed [24:0] operand_a;
    reg signed [17:0] operand_b;
    (* use_dsp = "yes" *) reg signed [42:0] multiplication;
    reg valid_a, valid_m, mode_a, mode_m;
    wire signed [24:0] high_weight = {{1{weight1[7]}}, weight1, 16'b0};
    wire signed [24:0] low_weight = {{17{weight0[7]}}, weight0};
    always @(posedge clk) begin
        if (reset) begin
            valid_a <= 0;
            valid_m <= 0;
            valid_out <= 0;
        end else if (ce) begin
            valid_a <= valid_in;
            mode_a <= square_mode;
            operand_a <= square_mode ? {{8{difference[16]}}, difference}
                                     : high_weight + low_weight;
            operand_b <= square_mode ? {difference[16], difference}
                                     : {{10{activation[7]}}, activation};
            valid_m <= valid_a;
            mode_m <= mode_a;
            multiplication <= operand_a * operand_b;
            valid_out <= valid_m;
            square_out <= mode_m;
            product0 <= multiplication[15:0];
            // A negative low product borrows one from the packed upper product.
            product1 <= $signed(multiplication[31:16]) +
                        $signed({15'b0, multiplication[15]});
            squared <= multiplication[33:0];
        end
    end
endmodule
