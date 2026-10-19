`timescale 1ns/1ps
module tb_region_identity_v156;
 reg clk=0,rstn=0;always #5 clk=~clk;
 reg [831:0] snap=0;reg [11:0] awaddr=0,araddr=0;reg av=0,wv=0,br=0,rv=0,rr=0;
 string result;integer proof;
 wire awr,wr,bv,arr,rvalid;wire [31:0] data;wire [1:0] bp,rp;integer i;
 region_axi dut(clk,rstn,snap,awaddr,3'b0,av,awr,32'b0,4'hf,wv,wr,bp,bv,br,araddr,3'b0,rv,arr,data,rp,rvalid,rr);
 task readword(input integer addr,input [31:0] expected);
  begin
   @(negedge clk);araddr=addr;rv=1;@(negedge clk);rv=0;
   if(!rvalid || data!==expected || rp!==0)$fatal(1,"read %d data=%h expected=%h",addr,data,expected);
   repeat(3)begin @(negedge clk);if(!rvalid || data!==expected)$fatal(1,"R unstable under backpressure");end
   rr=1;@(negedge clk);rr=0;if(rvalid)$fatal(1,"R not consumed");
  end
 endtask
 initial begin
  for(i=0;i<26;i=i+1)snap[i*32+:32]=32'ha0000000+i;
  repeat(5)@(negedge clk);rstn=1;
  for(i=0;i<26;i=i+1)readword(i*4,32'ha0000000+i);
  readword(104,0);readword(4092,0);
  readword(256,32'hd202c7e3);readword(260,32'h00012e00);readword(264,32'd65536);readword(268,-32'sd393216);
  @(negedge clk);wv=1;@(negedge clk);wv=0;repeat(4)@(negedge clk);if(bv)$fatal(1,"B before AW");
  av=1;@(negedge clk);av=0;repeat(3)@(negedge clk);
  if(!bv || bp!==2)$fatal(1,"write must return SLVERR");
  br=1;@(negedge clk);br=0;if(bv)$fatal(1,"B not consumed");
  readword(0,32'ha0000000);if(!$value$plusargs("RESULT=%s",result))$fatal(1,"missing RESULT");proof=$fopen(result,"w");$fdisplay(proof,"PASS 26 snapshot registers plus model identity/version/high/gate; read backpressure; writes rejected");$fclose(proof);$display("REGION AXI PASS 26 registers, invalid address, read backpressure and separated AW/W");$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
