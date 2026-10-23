module tb_packed_pe;
    reg clk=0, reset=1, ce=0, valid_in=0, square_mode=0;
    reg signed [7:0] activation=0, weight0=0, weight1=0;
    reg signed [16:0] difference=0;
    wire valid_out, square_out;
    wire signed [15:0] product0, product1;
    wire [33:0] squared;
    packed_pe dut(.*);
    always #5 clk=~clk;
    reg [2:0] v=0, m=0;
    reg signed [15:0] p0[0:2],p1[0:2];
    reg [33:0] sq[0:2];
    reg signed [63:0] wide_d;
    integer checked=0, stalled=0, flushed=0, i,j,k,n;
    integer activations[0:6];
    reg [31:0] rng=32'h3a57912b;
    always @(posedge clk) begin
        if(reset) begin
            if(v != 0) flushed=flushed+1;
            v=0;
        end else if(ce) begin
            v={v[1:0],valid_in}; m={m[1:0],square_mode};
            p0[2]=p0[1]; p0[1]=p0[0]; p0[0]=$signed(activation)*$signed(weight0);
            p1[2]=p1[1]; p1[1]=p1[0]; p1[0]=$signed(activation)*$signed(weight1);
            sq[2]=sq[1]; sq[1]=sq[0]; wide_d=difference; sq[0]=wide_d*wide_d;
        end else stalled=stalled+1;
        #1;
        if(valid_out !== v[2]) $fatal(1,"valid mismatch");
        if(valid_out) begin
            if(square_out !== m[2]) $fatal(1,"mode mismatch");
            if(square_out) begin
                if(squared !== sq[2]) $fatal(1,"square mismatch got %d expected %d",squared,sq[2]);
            end else if(product0 !== p0[2] || product1 !== p1[2])
                $fatal(1,"packed mismatch got %d %d expected %d %d",product0,product1,p0[2],p1[2]);
            if(ce && !reset) checked=checked+1;
        end
    end
    task drive(input integer a,w0,w1,d,mode,valid);
        begin
            @(negedge clk);
            rng=rng ^ (rng<<13); rng=rng ^ (rng>>17); rng=rng ^ (rng<<5);
            ce=(rng[3:0]!=0); valid_in=valid; square_mode=mode;
            activation=a;weight0=w0;weight1=w1;difference=d;
            // Inputs may change during a stall. Retry the same transaction next cycle.
            while(!ce) begin
                @(negedge clk); ce=1;
            end
        end
    endtask
    initial begin
        activations[0]=-128;activations[1]=-127;activations[2]=-1;
        activations[3]=0;activations[4]=1;activations[5]=126;activations[6]=127;
        repeat(2) @(negedge clk);reset=0;
        for(k=0;k<7;k=k+1)
            for(i=-128;i<128;i=i+1)
                for(j=-128;j<128;j=j+1) drive(activations[k],i,j,0,0,1);
        for(i=-65535;i<=65535;i=i+1) drive(0,0,0,i,1,1);
        for(n=0;n<32768;n=n+1) begin
            drive(rng[7:0],rng[15:8],rng[23:16],$signed(rng[16:0]),rng[24],rng[25:24]!=0);
            if(n%257==0) begin
                @(negedge clk);reset=1;ce=0;
                @(negedge clk);reset=0;
            end
        end
        repeat(4) drive(0,0,0,0,0,0);
        @(negedge clk);
        if(checked<610000 || stalled<1000 || flushed<10) $fatal(1,"coverage too small");
        $display("PACKED_PE_RTL_PASS checked=%0d stalled=%0d reset_flushes=%0d",checked,stalled,flushed);
        $finish;
    end
endmodule
