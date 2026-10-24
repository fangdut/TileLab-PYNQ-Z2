`timescale 1ns/1ps
module tb_generated_mac;
reg  ap_clk=0;
reg  ap_rst=0;
reg  ap_start=0;
reg  start_full_n=1;
wire  ap_done;
reg  ap_continue=0;
wire  ap_idle;
wire  ap_ready;
wire  start_out;
wire  start_write;
reg [127:0] dw_weight_0=0;
reg [127:0] dw_weight_1=0;
reg [127:0] dw_weight_2=0;
reg [127:0] dw_weight_3=0;
reg [127:0] dw_weight_4=0;
reg [127:0] dw_weight_5=0;
reg [127:0] dw_weight_6=0;
reg [127:0] dw_weight_7=0;
reg [127:0] dw_weight_8=0;
reg [15:0] query_0=0;
reg [15:0] query_1=0;
reg [15:0] query_2=0;
reg [15:0] query_3=0;
reg [15:0] query_4=0;
reg [15:0] query_5=0;
reg [15:0] query_6=0;
reg [15:0] query_7=0;
reg [15:0] query_8=0;
reg [15:0] query_9=0;
reg [15:0] query_10=0;
reg [15:0] query_11=0;
reg [15:0] query_12=0;
reg [15:0] query_13=0;
reg [15:0] query_14=0;
reg [15:0] query_15=0;
reg [15:0] query_16=0;
reg [15:0] query_17=0;
reg [15:0] query_18=0;
reg [15:0] query_19=0;
reg [15:0] query_20=0;
reg [15:0] query_21=0;
reg [15:0] query_22=0;
reg [15:0] query_23=0;
reg [15:0] query_24=0;
reg [15:0] query_25=0;
reg [15:0] query_26=0;
reg [15:0] query_27=0;
reg [15:0] query_28=0;
reg [15:0] query_29=0;
reg [15:0] query_30=0;
reg [15:0] query_31=0;
reg [15:0] query_32=0;
reg [15:0] query_33=0;
reg [15:0] query_34=0;
reg [15:0] query_35=0;
reg [15:0] query_36=0;
reg [15:0] query_37=0;
reg [15:0] query_38=0;
reg [15:0] query_39=0;
reg [15:0] query_40=0;
reg [15:0] query_41=0;
reg [15:0] query_42=0;
reg [15:0] query_43=0;
reg [15:0] query_44=0;
reg [15:0] query_45=0;
reg [15:0] query_46=0;
reg [15:0] query_47=0;
reg [15:0] query_48=0;
reg [15:0] query_49=0;
reg [15:0] query_50=0;
reg [15:0] query_51=0;
reg [15:0] query_52=0;
reg [15:0] query_53=0;
reg [15:0] query_54=0;
reg [15:0] query_55=0;
reg [15:0] query_56=0;
reg [15:0] query_57=0;
reg [15:0] query_58=0;
reg [15:0] query_59=0;
reg [15:0] query_60=0;
reg [15:0] query_61=0;
reg [15:0] query_62=0;
reg [15:0] query_63=0;
reg [9:0] ow=0;
reg [9:0] ic=0;
reg [9:0] iw=0;
reg [1:0] k=0;
reg [1:0] stride=0;
reg [0:0] pad=0;
reg [0:0] depth=0;
reg [1:0] row_head=0;
wire [9:0] ram_0_address0;
wire  ram_0_ce0;
reg [63:0] ram_0_q0=0;
wire [9:0] ram_0_address1;
wire  ram_0_ce1;
reg [63:0] ram_0_q1=0;
wire [9:0] ram_1_address0;
wire  ram_1_ce0;
reg [63:0] ram_1_q0=0;
wire [9:0] ram_1_address1;
wire  ram_1_ce1;
reg [63:0] ram_1_q1=0;
wire [9:0] ram_2_address0;
wire  ram_2_ce0;
reg [63:0] ram_2_q0=0;
wire [9:0] ram_2_address1;
wire  ram_2_ce1;
reg [63:0] ram_2_q1=0;
wire [9:0] ram_3_address0;
wire  ram_3_ce0;
reg [63:0] ram_3_q0=0;
wire [9:0] ram_3_address1;
wire  ram_3_ce1;
reg [63:0] ram_3_q1=0;
wire [9:0] ram_4_address0;
wire  ram_4_ce0;
reg [63:0] ram_4_q0=0;
wire [9:0] ram_4_address1;
wire  ram_4_ce1;
reg [63:0] ram_4_q1=0;
wire [9:0] ram_5_address0;
wire  ram_5_ce0;
reg [63:0] ram_5_q0=0;
wire [9:0] ram_5_address1;
wire  ram_5_ce1;
reg [63:0] ram_5_q1=0;
wire [9:0] ram_6_address0;
wire  ram_6_ce0;
reg [63:0] ram_6_q0=0;
wire [9:0] ram_6_address1;
wire  ram_6_ce1;
reg [63:0] ram_6_q1=0;
wire [9:0] ram_7_address0;
wire  ram_7_ce0;
reg [63:0] ram_7_q0=0;
wire [9:0] ram_7_address1;
wire  ram_7_ce1;
reg [63:0] ram_7_q1=0;
wire [9:0] ram_8_address0;
wire  ram_8_ce0;
reg [63:0] ram_8_q0=0;
wire [9:0] ram_8_address1;
wire  ram_8_ce1;
reg [63:0] ram_8_q1=0;
wire [9:0] ram_9_address0;
wire  ram_9_ce0;
reg [63:0] ram_9_q0=0;
wire [9:0] ram_9_address1;
wire  ram_9_ce1;
reg [63:0] ram_9_q1=0;
wire [9:0] ram_10_address0;
wire  ram_10_ce0;
reg [63:0] ram_10_q0=0;
wire [9:0] ram_10_address1;
wire  ram_10_ce1;
reg [63:0] ram_10_q1=0;
wire [9:0] ram_11_address0;
wire  ram_11_ce0;
reg [63:0] ram_11_q0=0;
wire [9:0] ram_11_address1;
wire  ram_11_ce1;
reg [63:0] ram_11_q1=0;
wire [9:0] ram_12_address0;
wire  ram_12_ce0;
reg [63:0] ram_12_q0=0;
wire [9:0] ram_12_address1;
wire  ram_12_ce1;
reg [63:0] ram_12_q1=0;
wire [9:0] ram_13_address0;
wire  ram_13_ce0;
reg [63:0] ram_13_q0=0;
wire [9:0] ram_13_address1;
wire  ram_13_ce1;
reg [63:0] ram_13_q1=0;
wire [9:0] ram_14_address0;
wire  ram_14_ce0;
reg [63:0] ram_14_q0=0;
wire [9:0] ram_14_address1;
wire  ram_14_ce1;
reg [63:0] ram_14_q1=0;
wire [9:0] ram_15_address0;
wire  ram_15_ce0;
reg [63:0] ram_15_q0=0;
wire [9:0] ram_15_address1;
wire  ram_15_ce1;
reg [63:0] ram_15_q1=0;
wire [10:0] line_r_address0;
wire  line_r_ce0;
reg [127:0] line_r_q0=0;
wire [10:0] line_r_address1;
wire  line_r_ce1;
reg [127:0] line_r_q1=0;
reg [0:0] nearest=0;
reg [10:0] count=0;
wire [1023:0] sums_din;
reg  sums_full_n=1;
wire  sums_write;
reg [4:0] sums_num_data_valid=0;
reg [4:0] sums_fifo_cap=0;
always #5 ap_clk=~ap_clk;
texture_integer_mac_row dut(.ap_clk(ap_clk),.ap_rst(ap_rst),.ap_start(ap_start),.start_full_n(start_full_n),.ap_done(ap_done),.ap_continue(ap_continue),.ap_idle(ap_idle),.ap_ready(ap_ready),.start_out(start_out),.start_write(start_write),.dw_weight_0(dw_weight_0),.dw_weight_1(dw_weight_1),.dw_weight_2(dw_weight_2),.dw_weight_3(dw_weight_3),.dw_weight_4(dw_weight_4),.dw_weight_5(dw_weight_5),.dw_weight_6(dw_weight_6),.dw_weight_7(dw_weight_7),.dw_weight_8(dw_weight_8),.query_0(query_0),.query_1(query_1),.query_2(query_2),.query_3(query_3),.query_4(query_4),.query_5(query_5),.query_6(query_6),.query_7(query_7),.query_8(query_8),.query_9(query_9),.query_10(query_10),.query_11(query_11),.query_12(query_12),.query_13(query_13),.query_14(query_14),.query_15(query_15),.query_16(query_16),.query_17(query_17),.query_18(query_18),.query_19(query_19),.query_20(query_20),.query_21(query_21),.query_22(query_22),.query_23(query_23),.query_24(query_24),.query_25(query_25),.query_26(query_26),.query_27(query_27),.query_28(query_28),.query_29(query_29),.query_30(query_30),.query_31(query_31),.query_32(query_32),.query_33(query_33),.query_34(query_34),.query_35(query_35),.query_36(query_36),.query_37(query_37),.query_38(query_38),.query_39(query_39),.query_40(query_40),.query_41(query_41),.query_42(query_42),.query_43(query_43),.query_44(query_44),.query_45(query_45),.query_46(query_46),.query_47(query_47),.query_48(query_48),.query_49(query_49),.query_50(query_50),.query_51(query_51),.query_52(query_52),.query_53(query_53),.query_54(query_54),.query_55(query_55),.query_56(query_56),.query_57(query_57),.query_58(query_58),.query_59(query_59),.query_60(query_60),.query_61(query_61),.query_62(query_62),.query_63(query_63),.ow(ow),.ic(ic),.iw(iw),.k(k),.stride(stride),.pad(pad),.depth(depth),.row_head(row_head),.ram_0_address0(ram_0_address0),.ram_0_ce0(ram_0_ce0),.ram_0_q0(ram_0_q0),.ram_0_address1(ram_0_address1),.ram_0_ce1(ram_0_ce1),.ram_0_q1(ram_0_q1),.ram_1_address0(ram_1_address0),.ram_1_ce0(ram_1_ce0),.ram_1_q0(ram_1_q0),.ram_1_address1(ram_1_address1),.ram_1_ce1(ram_1_ce1),.ram_1_q1(ram_1_q1),.ram_2_address0(ram_2_address0),.ram_2_ce0(ram_2_ce0),.ram_2_q0(ram_2_q0),.ram_2_address1(ram_2_address1),.ram_2_ce1(ram_2_ce1),.ram_2_q1(ram_2_q1),.ram_3_address0(ram_3_address0),.ram_3_ce0(ram_3_ce0),.ram_3_q0(ram_3_q0),.ram_3_address1(ram_3_address1),.ram_3_ce1(ram_3_ce1),.ram_3_q1(ram_3_q1),.ram_4_address0(ram_4_address0),.ram_4_ce0(ram_4_ce0),.ram_4_q0(ram_4_q0),.ram_4_address1(ram_4_address1),.ram_4_ce1(ram_4_ce1),.ram_4_q1(ram_4_q1),.ram_5_address0(ram_5_address0),.ram_5_ce0(ram_5_ce0),.ram_5_q0(ram_5_q0),.ram_5_address1(ram_5_address1),.ram_5_ce1(ram_5_ce1),.ram_5_q1(ram_5_q1),.ram_6_address0(ram_6_address0),.ram_6_ce0(ram_6_ce0),.ram_6_q0(ram_6_q0),.ram_6_address1(ram_6_address1),.ram_6_ce1(ram_6_ce1),.ram_6_q1(ram_6_q1),.ram_7_address0(ram_7_address0),.ram_7_ce0(ram_7_ce0),.ram_7_q0(ram_7_q0),.ram_7_address1(ram_7_address1),.ram_7_ce1(ram_7_ce1),.ram_7_q1(ram_7_q1),.ram_8_address0(ram_8_address0),.ram_8_ce0(ram_8_ce0),.ram_8_q0(ram_8_q0),.ram_8_address1(ram_8_address1),.ram_8_ce1(ram_8_ce1),.ram_8_q1(ram_8_q1),.ram_9_address0(ram_9_address0),.ram_9_ce0(ram_9_ce0),.ram_9_q0(ram_9_q0),.ram_9_address1(ram_9_address1),.ram_9_ce1(ram_9_ce1),.ram_9_q1(ram_9_q1),.ram_10_address0(ram_10_address0),.ram_10_ce0(ram_10_ce0),.ram_10_q0(ram_10_q0),.ram_10_address1(ram_10_address1),.ram_10_ce1(ram_10_ce1),.ram_10_q1(ram_10_q1),.ram_11_address0(ram_11_address0),.ram_11_ce0(ram_11_ce0),.ram_11_q0(ram_11_q0),.ram_11_address1(ram_11_address1),.ram_11_ce1(ram_11_ce1),.ram_11_q1(ram_11_q1),.ram_12_address0(ram_12_address0),.ram_12_ce0(ram_12_ce0),.ram_12_q0(ram_12_q0),.ram_12_address1(ram_12_address1),.ram_12_ce1(ram_12_ce1),.ram_12_q1(ram_12_q1),.ram_13_address0(ram_13_address0),.ram_13_ce0(ram_13_ce0),.ram_13_q0(ram_13_q0),.ram_13_address1(ram_13_address1),.ram_13_ce1(ram_13_ce1),.ram_13_q1(ram_13_q1),.ram_14_address0(ram_14_address0),.ram_14_ce0(ram_14_ce0),.ram_14_q0(ram_14_q0),.ram_14_address1(ram_14_address1),.ram_14_ce1(ram_14_ce1),.ram_14_q1(ram_14_q1),.ram_15_address0(ram_15_address0),.ram_15_ce0(ram_15_ce0),.ram_15_q0(ram_15_q0),.ram_15_address1(ram_15_address1),.ram_15_ce1(ram_15_ce1),.ram_15_q1(ram_15_q1),.line_r_address0(line_r_address0),.line_r_ce0(line_r_ce0),.line_r_q0(line_r_q0),.line_r_address1(line_r_address1),.line_r_ce1(line_r_ce1),.line_r_q1(line_r_q1),.nearest(nearest),.count(count),.sums_din(sums_din),.sums_full_n(sums_full_n),.sums_write(sums_write),.sums_num_data_valid(sums_num_data_valid),.sums_fifo_cap(sums_fifo_cap));
reg [63:0] memory[0:15][0:1023]; reg [127:0] pixels[0:2047],dw[0:8];reg [15:0] query_data[0:63];reg [1023:0] expected[0:511];
integer cycle=0,seen=0,total=0,active_case=0,want=0,stalled=0;reg done_seen=0;
always @(negedge ap_clk) begin cycle=cycle+1; sums_full_n=((cycle%7)!=0)&&((cycle%11)!=0);sums_num_data_valid=sums_full_n?0:16; end
always @(posedge ap_clk) begin
if(!ap_rst && sums_write && sums_full_n) begin if(seen>=want || sums_din !== expected[seen]) $fatal(1,"MAC_MISMATCH case=%0d output=%0d got=%h expected=%h",active_case,seen,sums_din,expected[seen]);seen=seen+1;total=total+1; end
if(!ap_rst && !sums_full_n && active_case>0)stalled=stalled+1;
if(ram_0_ce0)ram_0_q0<=memory[0][ram_0_address0];
if(ram_0_ce1)ram_0_q1<=memory[0][ram_0_address1];
if(ram_1_ce0)ram_1_q0<=memory[1][ram_1_address0];
if(ram_1_ce1)ram_1_q1<=memory[1][ram_1_address1];
if(ram_2_ce0)ram_2_q0<=memory[2][ram_2_address0];
if(ram_2_ce1)ram_2_q1<=memory[2][ram_2_address1];
if(ram_3_ce0)ram_3_q0<=memory[3][ram_3_address0];
if(ram_3_ce1)ram_3_q1<=memory[3][ram_3_address1];
if(ram_4_ce0)ram_4_q0<=memory[4][ram_4_address0];
if(ram_4_ce1)ram_4_q1<=memory[4][ram_4_address1];
if(ram_5_ce0)ram_5_q0<=memory[5][ram_5_address0];
if(ram_5_ce1)ram_5_q1<=memory[5][ram_5_address1];
if(ram_6_ce0)ram_6_q0<=memory[6][ram_6_address0];
if(ram_6_ce1)ram_6_q1<=memory[6][ram_6_address1];
if(ram_7_ce0)ram_7_q0<=memory[7][ram_7_address0];
if(ram_7_ce1)ram_7_q1<=memory[7][ram_7_address1];
if(ram_8_ce0)ram_8_q0<=memory[8][ram_8_address0];
if(ram_8_ce1)ram_8_q1<=memory[8][ram_8_address1];
if(ram_9_ce0)ram_9_q0<=memory[9][ram_9_address0];
if(ram_9_ce1)ram_9_q1<=memory[9][ram_9_address1];
if(ram_10_ce0)ram_10_q0<=memory[10][ram_10_address0];
if(ram_10_ce1)ram_10_q1<=memory[10][ram_10_address1];
if(ram_11_ce0)ram_11_q0<=memory[11][ram_11_address0];
if(ram_11_ce1)ram_11_q1<=memory[11][ram_11_address1];
if(ram_12_ce0)ram_12_q0<=memory[12][ram_12_address0];
if(ram_12_ce1)ram_12_q1<=memory[12][ram_12_address1];
if(ram_13_ce0)ram_13_q0<=memory[13][ram_13_address0];
if(ram_13_ce1)ram_13_q1<=memory[13][ram_13_address1];
if(ram_14_ce0)ram_14_q0<=memory[14][ram_14_address0];
if(ram_14_ce1)ram_14_q1<=memory[14][ram_14_address1];
if(ram_15_ce0)ram_15_q0<=memory[15][ram_15_address0];
if(ram_15_ce1)ram_15_q1<=memory[15][ram_15_address1];
if(line_r_ce0)line_r_q0<=pixels[line_r_address0];if(line_r_ce1)line_r_q1<=pixels[line_r_address1];
if(!ap_rst && ap_done)done_seen=1;
end
initial begin ap_rst=1;ap_continue=1;sums_fifo_cap=16;repeat(6)@(negedge ap_clk);ap_rst=0;
@(negedge ap_clk);active_case=1;seen=0;done_seen=0;want=17;
begin : load_1_0 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram0.mem",temp);for(n=0;n<1024;n=n+1)memory[0][n]=temp[n];end
begin : load_1_1 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram1.mem",temp);for(n=0;n<1024;n=n+1)memory[1][n]=temp[n];end
begin : load_1_2 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram2.mem",temp);for(n=0;n<1024;n=n+1)memory[2][n]=temp[n];end
begin : load_1_3 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram3.mem",temp);for(n=0;n<1024;n=n+1)memory[3][n]=temp[n];end
begin : load_1_4 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram4.mem",temp);for(n=0;n<1024;n=n+1)memory[4][n]=temp[n];end
begin : load_1_5 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram5.mem",temp);for(n=0;n<1024;n=n+1)memory[5][n]=temp[n];end
begin : load_1_6 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram6.mem",temp);for(n=0;n<1024;n=n+1)memory[6][n]=temp[n];end
begin : load_1_7 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram7.mem",temp);for(n=0;n<1024;n=n+1)memory[7][n]=temp[n];end
begin : load_1_8 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram8.mem",temp);for(n=0;n<1024;n=n+1)memory[8][n]=temp[n];end
begin : load_1_9 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram9.mem",temp);for(n=0;n<1024;n=n+1)memory[9][n]=temp[n];end
begin : load_1_10 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram10.mem",temp);for(n=0;n<1024;n=n+1)memory[10][n]=temp[n];end
begin : load_1_11 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram11.mem",temp);for(n=0;n<1024;n=n+1)memory[11][n]=temp[n];end
begin : load_1_12 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram12.mem",temp);for(n=0;n<1024;n=n+1)memory[12][n]=temp[n];end
begin : load_1_13 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram13.mem",temp);for(n=0;n<1024;n=n+1)memory[13][n]=temp[n];end
begin : load_1_14 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram14.mem",temp);for(n=0;n<1024;n=n+1)memory[14][n]=temp[n];end
begin : load_1_15 reg [63:0] temp[0:1023];integer n;$readmemh("case1_ram15.mem",temp);for(n=0;n<1024;n=n+1)memory[15][n]=temp[n];end
$readmemh("case1_line.mem",pixels);
$readmemh("case1_dw.mem",dw);
$readmemh("case1_query.mem",query_data);
$readmemh("case1_expected.mem",expected,0,16);
ow=33;
ic=576;
iw=33;
k=1;
stride=1;
pad=0;
depth=0;
row_head=0;
nearest=0;
count=1;
dw_weight_0=dw[0];
dw_weight_1=dw[1];
dw_weight_2=dw[2];
dw_weight_3=dw[3];
dw_weight_4=dw[4];
dw_weight_5=dw[5];
dw_weight_6=dw[6];
dw_weight_7=dw[7];
dw_weight_8=dw[8];
query_0=query_data[0];
query_1=query_data[1];
query_2=query_data[2];
query_3=query_data[3];
query_4=query_data[4];
query_5=query_data[5];
query_6=query_data[6];
query_7=query_data[7];
query_8=query_data[8];
query_9=query_data[9];
query_10=query_data[10];
query_11=query_data[11];
query_12=query_data[12];
query_13=query_data[13];
query_14=query_data[14];
query_15=query_data[15];
query_16=query_data[16];
query_17=query_data[17];
query_18=query_data[18];
query_19=query_data[19];
query_20=query_data[20];
query_21=query_data[21];
query_22=query_data[22];
query_23=query_data[23];
query_24=query_data[24];
query_25=query_data[25];
query_26=query_data[26];
query_27=query_data[27];
query_28=query_data[28];
query_29=query_data[29];
query_30=query_data[30];
query_31=query_data[31];
query_32=query_data[32];
query_33=query_data[33];
query_34=query_data[34];
query_35=query_data[35];
query_36=query_data[36];
query_37=query_data[37];
query_38=query_data[38];
query_39=query_data[39];
query_40=query_data[40];
query_41=query_data[41];
query_42=query_data[42];
query_43=query_data[43];
query_44=query_data[44];
query_45=query_data[45];
query_46=query_data[46];
query_47=query_data[47];
query_48=query_data[48];
query_49=query_data[49];
query_50=query_data[50];
query_51=query_data[51];
query_52=query_data[52];
query_53=query_data[53];
query_54=query_data[54];
query_55=query_data[55];
query_56=query_data[56];
query_57=query_data[57];
query_58=query_data[58];
query_59=query_data[59];
query_60=query_data[60];
query_61=query_data[61];
query_62=query_data[62];
query_63=query_data[63];
@(negedge ap_clk);ap_start=1;@(negedge ap_clk);ap_start=0;
while(!done_seen)@(negedge ap_clk);
if(seen!=want)$fatal(1,"MAC_COUNT case=1 got=%0d expected=%0d",seen,want);
$display("MAC_CASE_PASS case=1 outputs=%0d cycle=%0d",seen,cycle);
repeat(6)@(negedge ap_clk);
@(negedge ap_clk);active_case=2;seen=0;done_seen=0;want=9;
begin : load_2_0 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram0.mem",temp);for(n=0;n<1024;n=n+1)memory[0][n]=temp[n];end
begin : load_2_1 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram1.mem",temp);for(n=0;n<1024;n=n+1)memory[1][n]=temp[n];end
begin : load_2_2 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram2.mem",temp);for(n=0;n<1024;n=n+1)memory[2][n]=temp[n];end
begin : load_2_3 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram3.mem",temp);for(n=0;n<1024;n=n+1)memory[3][n]=temp[n];end
begin : load_2_4 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram4.mem",temp);for(n=0;n<1024;n=n+1)memory[4][n]=temp[n];end
begin : load_2_5 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram5.mem",temp);for(n=0;n<1024;n=n+1)memory[5][n]=temp[n];end
begin : load_2_6 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram6.mem",temp);for(n=0;n<1024;n=n+1)memory[6][n]=temp[n];end
begin : load_2_7 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram7.mem",temp);for(n=0;n<1024;n=n+1)memory[7][n]=temp[n];end
begin : load_2_8 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram8.mem",temp);for(n=0;n<1024;n=n+1)memory[8][n]=temp[n];end
begin : load_2_9 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram9.mem",temp);for(n=0;n<1024;n=n+1)memory[9][n]=temp[n];end
begin : load_2_10 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram10.mem",temp);for(n=0;n<1024;n=n+1)memory[10][n]=temp[n];end
begin : load_2_11 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram11.mem",temp);for(n=0;n<1024;n=n+1)memory[11][n]=temp[n];end
begin : load_2_12 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram12.mem",temp);for(n=0;n<1024;n=n+1)memory[12][n]=temp[n];end
begin : load_2_13 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram13.mem",temp);for(n=0;n<1024;n=n+1)memory[13][n]=temp[n];end
begin : load_2_14 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram14.mem",temp);for(n=0;n<1024;n=n+1)memory[14][n]=temp[n];end
begin : load_2_15 reg [63:0] temp[0:1023];integer n;$readmemh("case2_ram15.mem",temp);for(n=0;n<1024;n=n+1)memory[15][n]=temp[n];end
$readmemh("case2_line.mem",pixels);
$readmemh("case2_dw.mem",dw);
$readmemh("case2_query.mem",query_data);
$readmemh("case2_expected.mem",expected,0,8);
ow=17;
ic=3;
iw=33;
k=3;
stride=2;
pad=1;
depth=0;
row_head=0;
nearest=0;
count=1;
dw_weight_0=dw[0];
dw_weight_1=dw[1];
dw_weight_2=dw[2];
dw_weight_3=dw[3];
dw_weight_4=dw[4];
dw_weight_5=dw[5];
dw_weight_6=dw[6];
dw_weight_7=dw[7];
dw_weight_8=dw[8];
query_0=query_data[0];
query_1=query_data[1];
query_2=query_data[2];
query_3=query_data[3];
query_4=query_data[4];
query_5=query_data[5];
query_6=query_data[6];
query_7=query_data[7];
query_8=query_data[8];
query_9=query_data[9];
query_10=query_data[10];
query_11=query_data[11];
query_12=query_data[12];
query_13=query_data[13];
query_14=query_data[14];
query_15=query_data[15];
query_16=query_data[16];
query_17=query_data[17];
query_18=query_data[18];
query_19=query_data[19];
query_20=query_data[20];
query_21=query_data[21];
query_22=query_data[22];
query_23=query_data[23];
query_24=query_data[24];
query_25=query_data[25];
query_26=query_data[26];
query_27=query_data[27];
query_28=query_data[28];
query_29=query_data[29];
query_30=query_data[30];
query_31=query_data[31];
query_32=query_data[32];
query_33=query_data[33];
query_34=query_data[34];
query_35=query_data[35];
query_36=query_data[36];
query_37=query_data[37];
query_38=query_data[38];
query_39=query_data[39];
query_40=query_data[40];
query_41=query_data[41];
query_42=query_data[42];
query_43=query_data[43];
query_44=query_data[44];
query_45=query_data[45];
query_46=query_data[46];
query_47=query_data[47];
query_48=query_data[48];
query_49=query_data[49];
query_50=query_data[50];
query_51=query_data[51];
query_52=query_data[52];
query_53=query_data[53];
query_54=query_data[54];
query_55=query_data[55];
query_56=query_data[56];
query_57=query_data[57];
query_58=query_data[58];
query_59=query_data[59];
query_60=query_data[60];
query_61=query_data[61];
query_62=query_data[62];
query_63=query_data[63];
@(negedge ap_clk);ap_start=1;@(negedge ap_clk);ap_start=0;
while(!done_seen)@(negedge ap_clk);
if(seen!=want)$fatal(1,"MAC_COUNT case=2 got=%0d expected=%0d",seen,want);
$display("MAC_CASE_PASS case=2 outputs=%0d cycle=%0d",seen,cycle);
repeat(6)@(negedge ap_clk);
@(negedge ap_clk);active_case=3;seen=0;done_seen=0;want=33;
begin : load_3_0 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram0.mem",temp);for(n=0;n<1024;n=n+1)memory[0][n]=temp[n];end
begin : load_3_1 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram1.mem",temp);for(n=0;n<1024;n=n+1)memory[1][n]=temp[n];end
begin : load_3_2 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram2.mem",temp);for(n=0;n<1024;n=n+1)memory[2][n]=temp[n];end
begin : load_3_3 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram3.mem",temp);for(n=0;n<1024;n=n+1)memory[3][n]=temp[n];end
begin : load_3_4 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram4.mem",temp);for(n=0;n<1024;n=n+1)memory[4][n]=temp[n];end
begin : load_3_5 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram5.mem",temp);for(n=0;n<1024;n=n+1)memory[5][n]=temp[n];end
begin : load_3_6 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram6.mem",temp);for(n=0;n<1024;n=n+1)memory[6][n]=temp[n];end
begin : load_3_7 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram7.mem",temp);for(n=0;n<1024;n=n+1)memory[7][n]=temp[n];end
begin : load_3_8 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram8.mem",temp);for(n=0;n<1024;n=n+1)memory[8][n]=temp[n];end
begin : load_3_9 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram9.mem",temp);for(n=0;n<1024;n=n+1)memory[9][n]=temp[n];end
begin : load_3_10 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram10.mem",temp);for(n=0;n<1024;n=n+1)memory[10][n]=temp[n];end
begin : load_3_11 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram11.mem",temp);for(n=0;n<1024;n=n+1)memory[11][n]=temp[n];end
begin : load_3_12 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram12.mem",temp);for(n=0;n<1024;n=n+1)memory[12][n]=temp[n];end
begin : load_3_13 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram13.mem",temp);for(n=0;n<1024;n=n+1)memory[13][n]=temp[n];end
begin : load_3_14 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram14.mem",temp);for(n=0;n<1024;n=n+1)memory[14][n]=temp[n];end
begin : load_3_15 reg [63:0] temp[0:1023];integer n;$readmemh("case3_ram15.mem",temp);for(n=0;n<1024;n=n+1)memory[15][n]=temp[n];end
$readmemh("case3_line.mem",pixels);
$readmemh("case3_dw.mem",dw);
$readmemh("case3_query.mem",query_data);
$readmemh("case3_expected.mem",expected,0,32);
ow=33;
ic=16;
iw=33;
k=3;
stride=1;
pad=1;
depth=1;
row_head=2;
nearest=0;
count=1;
dw_weight_0=dw[0];
dw_weight_1=dw[1];
dw_weight_2=dw[2];
dw_weight_3=dw[3];
dw_weight_4=dw[4];
dw_weight_5=dw[5];
dw_weight_6=dw[6];
dw_weight_7=dw[7];
dw_weight_8=dw[8];
query_0=query_data[0];
query_1=query_data[1];
query_2=query_data[2];
query_3=query_data[3];
query_4=query_data[4];
query_5=query_data[5];
query_6=query_data[6];
query_7=query_data[7];
query_8=query_data[8];
query_9=query_data[9];
query_10=query_data[10];
query_11=query_data[11];
query_12=query_data[12];
query_13=query_data[13];
query_14=query_data[14];
query_15=query_data[15];
query_16=query_data[16];
query_17=query_data[17];
query_18=query_data[18];
query_19=query_data[19];
query_20=query_data[20];
query_21=query_data[21];
query_22=query_data[22];
query_23=query_data[23];
query_24=query_data[24];
query_25=query_data[25];
query_26=query_data[26];
query_27=query_data[27];
query_28=query_data[28];
query_29=query_data[29];
query_30=query_data[30];
query_31=query_data[31];
query_32=query_data[32];
query_33=query_data[33];
query_34=query_data[34];
query_35=query_data[35];
query_36=query_data[36];
query_37=query_data[37];
query_38=query_data[38];
query_39=query_data[39];
query_40=query_data[40];
query_41=query_data[41];
query_42=query_data[42];
query_43=query_data[43];
query_44=query_data[44];
query_45=query_data[45];
query_46=query_data[46];
query_47=query_data[47];
query_48=query_data[48];
query_49=query_data[49];
query_50=query_data[50];
query_51=query_data[51];
query_52=query_data[52];
query_53=query_data[53];
query_54=query_data[54];
query_55=query_data[55];
query_56=query_data[56];
query_57=query_data[57];
query_58=query_data[58];
query_59=query_data[59];
query_60=query_data[60];
query_61=query_data[61];
query_62=query_data[62];
query_63=query_data[63];
@(negedge ap_clk);ap_start=1;@(negedge ap_clk);ap_start=0;
while(!done_seen)@(negedge ap_clk);
if(seen!=want)$fatal(1,"MAC_COUNT case=3 got=%0d expected=%0d",seen,want);
$display("MAC_CASE_PASS case=3 outputs=%0d cycle=%0d",seen,cycle);
repeat(6)@(negedge ap_clk);
@(negedge ap_clk);active_case=4;seen=0;done_seen=0;want=64;
begin : load_4_0 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram0.mem",temp);for(n=0;n<1024;n=n+1)memory[0][n]=temp[n];end
begin : load_4_1 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram1.mem",temp);for(n=0;n<1024;n=n+1)memory[1][n]=temp[n];end
begin : load_4_2 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram2.mem",temp);for(n=0;n<1024;n=n+1)memory[2][n]=temp[n];end
begin : load_4_3 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram3.mem",temp);for(n=0;n<1024;n=n+1)memory[3][n]=temp[n];end
begin : load_4_4 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram4.mem",temp);for(n=0;n<1024;n=n+1)memory[4][n]=temp[n];end
begin : load_4_5 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram5.mem",temp);for(n=0;n<1024;n=n+1)memory[5][n]=temp[n];end
begin : load_4_6 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram6.mem",temp);for(n=0;n<1024;n=n+1)memory[6][n]=temp[n];end
begin : load_4_7 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram7.mem",temp);for(n=0;n<1024;n=n+1)memory[7][n]=temp[n];end
begin : load_4_8 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram8.mem",temp);for(n=0;n<1024;n=n+1)memory[8][n]=temp[n];end
begin : load_4_9 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram9.mem",temp);for(n=0;n<1024;n=n+1)memory[9][n]=temp[n];end
begin : load_4_10 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram10.mem",temp);for(n=0;n<1024;n=n+1)memory[10][n]=temp[n];end
begin : load_4_11 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram11.mem",temp);for(n=0;n<1024;n=n+1)memory[11][n]=temp[n];end
begin : load_4_12 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram12.mem",temp);for(n=0;n<1024;n=n+1)memory[12][n]=temp[n];end
begin : load_4_13 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram13.mem",temp);for(n=0;n<1024;n=n+1)memory[13][n]=temp[n];end
begin : load_4_14 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram14.mem",temp);for(n=0;n<1024;n=n+1)memory[14][n]=temp[n];end
begin : load_4_15 reg [63:0] temp[0:1023];integer n;$readmemh("case4_ram15.mem",temp);for(n=0;n<1024;n=n+1)memory[15][n]=temp[n];end
$readmemh("case4_line.mem",pixels);
$readmemh("case4_dw.mem",dw);
$readmemh("case4_query.mem",query_data);
$readmemh("case4_expected.mem",expected,0,63);
ow=1;
ic=64;
iw=1;
k=1;
stride=1;
pad=0;
depth=0;
row_head=0;
nearest=1;
count=65;
dw_weight_0=dw[0];
dw_weight_1=dw[1];
dw_weight_2=dw[2];
dw_weight_3=dw[3];
dw_weight_4=dw[4];
dw_weight_5=dw[5];
dw_weight_6=dw[6];
dw_weight_7=dw[7];
dw_weight_8=dw[8];
query_0=query_data[0];
query_1=query_data[1];
query_2=query_data[2];
query_3=query_data[3];
query_4=query_data[4];
query_5=query_data[5];
query_6=query_data[6];
query_7=query_data[7];
query_8=query_data[8];
query_9=query_data[9];
query_10=query_data[10];
query_11=query_data[11];
query_12=query_data[12];
query_13=query_data[13];
query_14=query_data[14];
query_15=query_data[15];
query_16=query_data[16];
query_17=query_data[17];
query_18=query_data[18];
query_19=query_data[19];
query_20=query_data[20];
query_21=query_data[21];
query_22=query_data[22];
query_23=query_data[23];
query_24=query_data[24];
query_25=query_data[25];
query_26=query_data[26];
query_27=query_data[27];
query_28=query_data[28];
query_29=query_data[29];
query_30=query_data[30];
query_31=query_data[31];
query_32=query_data[32];
query_33=query_data[33];
query_34=query_data[34];
query_35=query_data[35];
query_36=query_data[36];
query_37=query_data[37];
query_38=query_data[38];
query_39=query_data[39];
query_40=query_data[40];
query_41=query_data[41];
query_42=query_data[42];
query_43=query_data[43];
query_44=query_data[44];
query_45=query_data[45];
query_46=query_data[46];
query_47=query_data[47];
query_48=query_data[48];
query_49=query_data[49];
query_50=query_data[50];
query_51=query_data[51];
query_52=query_data[52];
query_53=query_data[53];
query_54=query_data[54];
query_55=query_data[55];
query_56=query_data[56];
query_57=query_data[57];
query_58=query_data[58];
query_59=query_data[59];
query_60=query_data[60];
query_61=query_data[61];
query_62=query_data[62];
query_63=query_data[63];
@(negedge ap_clk);ap_start=1;@(negedge ap_clk);ap_start=0;
while(!done_seen)@(negedge ap_clk);
if(seen!=want)$fatal(1,"MAC_COUNT case=4 got=%0d expected=%0d",seen,want);
$display("MAC_CASE_PASS case=4 outputs=%0d cycle=%0d",seen,cycle);
repeat(6)@(negedge ap_clk);
@(negedge ap_clk);active_case=5;seen=0;done_seen=0;want=512;
begin : load_5_0 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram0.mem",temp);for(n=0;n<1024;n=n+1)memory[0][n]=temp[n];end
begin : load_5_1 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram1.mem",temp);for(n=0;n<1024;n=n+1)memory[1][n]=temp[n];end
begin : load_5_2 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram2.mem",temp);for(n=0;n<1024;n=n+1)memory[2][n]=temp[n];end
begin : load_5_3 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram3.mem",temp);for(n=0;n<1024;n=n+1)memory[3][n]=temp[n];end
begin : load_5_4 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram4.mem",temp);for(n=0;n<1024;n=n+1)memory[4][n]=temp[n];end
begin : load_5_5 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram5.mem",temp);for(n=0;n<1024;n=n+1)memory[5][n]=temp[n];end
begin : load_5_6 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram6.mem",temp);for(n=0;n<1024;n=n+1)memory[6][n]=temp[n];end
begin : load_5_7 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram7.mem",temp);for(n=0;n<1024;n=n+1)memory[7][n]=temp[n];end
begin : load_5_8 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram8.mem",temp);for(n=0;n<1024;n=n+1)memory[8][n]=temp[n];end
begin : load_5_9 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram9.mem",temp);for(n=0;n<1024;n=n+1)memory[9][n]=temp[n];end
begin : load_5_10 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram10.mem",temp);for(n=0;n<1024;n=n+1)memory[10][n]=temp[n];end
begin : load_5_11 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram11.mem",temp);for(n=0;n<1024;n=n+1)memory[11][n]=temp[n];end
begin : load_5_12 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram12.mem",temp);for(n=0;n<1024;n=n+1)memory[12][n]=temp[n];end
begin : load_5_13 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram13.mem",temp);for(n=0;n<1024;n=n+1)memory[13][n]=temp[n];end
begin : load_5_14 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram14.mem",temp);for(n=0;n<1024;n=n+1)memory[14][n]=temp[n];end
begin : load_5_15 reg [63:0] temp[0:1023];integer n;$readmemh("case5_ram15.mem",temp);for(n=0;n<1024;n=n+1)memory[15][n]=temp[n];end
$readmemh("case5_line.mem",pixels);
$readmemh("case5_dw.mem",dw);
$readmemh("case5_query.mem",query_data);
$readmemh("case5_expected.mem",expected,0,511);
ow=1;
ic=64;
iw=1;
k=1;
stride=1;
pad=0;
depth=0;
row_head=0;
nearest=1;
count=1024;
dw_weight_0=dw[0];
dw_weight_1=dw[1];
dw_weight_2=dw[2];
dw_weight_3=dw[3];
dw_weight_4=dw[4];
dw_weight_5=dw[5];
dw_weight_6=dw[6];
dw_weight_7=dw[7];
dw_weight_8=dw[8];
query_0=query_data[0];
query_1=query_data[1];
query_2=query_data[2];
query_3=query_data[3];
query_4=query_data[4];
query_5=query_data[5];
query_6=query_data[6];
query_7=query_data[7];
query_8=query_data[8];
query_9=query_data[9];
query_10=query_data[10];
query_11=query_data[11];
query_12=query_data[12];
query_13=query_data[13];
query_14=query_data[14];
query_15=query_data[15];
query_16=query_data[16];
query_17=query_data[17];
query_18=query_data[18];
query_19=query_data[19];
query_20=query_data[20];
query_21=query_data[21];
query_22=query_data[22];
query_23=query_data[23];
query_24=query_data[24];
query_25=query_data[25];
query_26=query_data[26];
query_27=query_data[27];
query_28=query_data[28];
query_29=query_data[29];
query_30=query_data[30];
query_31=query_data[31];
query_32=query_data[32];
query_33=query_data[33];
query_34=query_data[34];
query_35=query_data[35];
query_36=query_data[36];
query_37=query_data[37];
query_38=query_data[38];
query_39=query_data[39];
query_40=query_data[40];
query_41=query_data[41];
query_42=query_data[42];
query_43=query_data[43];
query_44=query_data[44];
query_45=query_data[45];
query_46=query_data[46];
query_47=query_data[47];
query_48=query_data[48];
query_49=query_data[49];
query_50=query_data[50];
query_51=query_data[51];
query_52=query_data[52];
query_53=query_data[53];
query_54=query_data[54];
query_55=query_data[55];
query_56=query_data[56];
query_57=query_data[57];
query_58=query_data[58];
query_59=query_data[59];
query_60=query_data[60];
query_61=query_data[61];
query_62=query_data[62];
query_63=query_data[63];
@(negedge ap_clk);ap_start=1;@(negedge ap_clk);ap_start=0;
while(!done_seen)@(negedge ap_clk);
if(seen!=want)$fatal(1,"MAC_COUNT case=5 got=%0d expected=%0d",seen,want);
$display("MAC_CASE_PASS case=5 outputs=%0d cycle=%0d",seen,cycle);
repeat(6)@(negedge ap_clk);
@(negedge ap_clk);active_case=6;seen=0;done_seen=0;want=7;
begin : load_6_0 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram0.mem",temp);for(n=0;n<1024;n=n+1)memory[0][n]=temp[n];end
begin : load_6_1 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram1.mem",temp);for(n=0;n<1024;n=n+1)memory[1][n]=temp[n];end
begin : load_6_2 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram2.mem",temp);for(n=0;n<1024;n=n+1)memory[2][n]=temp[n];end
begin : load_6_3 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram3.mem",temp);for(n=0;n<1024;n=n+1)memory[3][n]=temp[n];end
begin : load_6_4 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram4.mem",temp);for(n=0;n<1024;n=n+1)memory[4][n]=temp[n];end
begin : load_6_5 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram5.mem",temp);for(n=0;n<1024;n=n+1)memory[5][n]=temp[n];end
begin : load_6_6 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram6.mem",temp);for(n=0;n<1024;n=n+1)memory[6][n]=temp[n];end
begin : load_6_7 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram7.mem",temp);for(n=0;n<1024;n=n+1)memory[7][n]=temp[n];end
begin : load_6_8 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram8.mem",temp);for(n=0;n<1024;n=n+1)memory[8][n]=temp[n];end
begin : load_6_9 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram9.mem",temp);for(n=0;n<1024;n=n+1)memory[9][n]=temp[n];end
begin : load_6_10 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram10.mem",temp);for(n=0;n<1024;n=n+1)memory[10][n]=temp[n];end
begin : load_6_11 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram11.mem",temp);for(n=0;n<1024;n=n+1)memory[11][n]=temp[n];end
begin : load_6_12 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram12.mem",temp);for(n=0;n<1024;n=n+1)memory[12][n]=temp[n];end
begin : load_6_13 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram13.mem",temp);for(n=0;n<1024;n=n+1)memory[13][n]=temp[n];end
begin : load_6_14 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram14.mem",temp);for(n=0;n<1024;n=n+1)memory[14][n]=temp[n];end
begin : load_6_15 reg [63:0] temp[0:1023];integer n;$readmemh("case6_ram15.mem",temp);for(n=0;n<1024;n=n+1)memory[15][n]=temp[n];end
$readmemh("case6_line.mem",pixels);
$readmemh("case6_dw.mem",dw);
$readmemh("case6_query.mem",query_data);
$readmemh("case6_expected.mem",expected,0,6);
ow=14;
ic=24;
iw=14;
k=1;
stride=1;
pad=0;
depth=0;
row_head=0;
nearest=0;
count=1;
dw_weight_0=dw[0];
dw_weight_1=dw[1];
dw_weight_2=dw[2];
dw_weight_3=dw[3];
dw_weight_4=dw[4];
dw_weight_5=dw[5];
dw_weight_6=dw[6];
dw_weight_7=dw[7];
dw_weight_8=dw[8];
query_0=query_data[0];
query_1=query_data[1];
query_2=query_data[2];
query_3=query_data[3];
query_4=query_data[4];
query_5=query_data[5];
query_6=query_data[6];
query_7=query_data[7];
query_8=query_data[8];
query_9=query_data[9];
query_10=query_data[10];
query_11=query_data[11];
query_12=query_data[12];
query_13=query_data[13];
query_14=query_data[14];
query_15=query_data[15];
query_16=query_data[16];
query_17=query_data[17];
query_18=query_data[18];
query_19=query_data[19];
query_20=query_data[20];
query_21=query_data[21];
query_22=query_data[22];
query_23=query_data[23];
query_24=query_data[24];
query_25=query_data[25];
query_26=query_data[26];
query_27=query_data[27];
query_28=query_data[28];
query_29=query_data[29];
query_30=query_data[30];
query_31=query_data[31];
query_32=query_data[32];
query_33=query_data[33];
query_34=query_data[34];
query_35=query_data[35];
query_36=query_data[36];
query_37=query_data[37];
query_38=query_data[38];
query_39=query_data[39];
query_40=query_data[40];
query_41=query_data[41];
query_42=query_data[42];
query_43=query_data[43];
query_44=query_data[44];
query_45=query_data[45];
query_46=query_data[46];
query_47=query_data[47];
query_48=query_data[48];
query_49=query_data[49];
query_50=query_data[50];
query_51=query_data[51];
query_52=query_data[52];
query_53=query_data[53];
query_54=query_data[54];
query_55=query_data[55];
query_56=query_data[56];
query_57=query_data[57];
query_58=query_data[58];
query_59=query_data[59];
query_60=query_data[60];
query_61=query_data[61];
query_62=query_data[62];
query_63=query_data[63];
@(negedge ap_clk);ap_start=1;@(negedge ap_clk);ap_start=0;
while(!done_seen)@(negedge ap_clk);
if(seen!=want)$fatal(1,"MAC_COUNT case=6 got=%0d expected=%0d",seen,want);
$display("MAC_CASE_PASS case=6 outputs=%0d cycle=%0d",seen,cycle);
repeat(6)@(negedge ap_clk);
if(total!=642 || stalled==0)$fatal(1,"MAC_COVERAGE total=%0d stalled=%0d",total,stalled);
$display("GENERATED_PAIRED_MAC_RTL_PASS cases=6 outputs=%0d stalled=%0d cycles=%0d",total,stalled,cycle);$finish;end
initial begin #2000000;$fatal(1,"MAC_TIMEOUT");end
endmodule
