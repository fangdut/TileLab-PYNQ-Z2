`timescale 1ns/1ps
module tb_status_cdc;
reg pix=0,refclk=0,pix_run=1;always #6.734 if(pix_run) pix=~pix;always #2.5 refclk=~refclk;
reg [31:0] count=0;reg lock=0,hpd=1,fmt=0;
wire [31:0] value;wire [3:0] led;wire source_hpd;
status_cdc dut(pix,refclk,lock,hpd,fmt,count,value,led,source_hpd);
reg [31:0] old=0;
initial begin
 repeat(30) @(negedge pix);
 if(source_hpd!==0 || led[1]!==0) $fatal(1,"Disconnected HPDN=1 must not assert source HPD");
 lock=1;hpd=0;fmt=1;
 repeat(30) @(negedge refclk);
 if(source_hpd!==1 || led[1]!==1) $fatal(1,"Connected HPDN=0 must assert source HPD");
 for(integer i=0;i<100;i=i+1) begin
  @(negedge pix);old=count;count=$urandom;
  for(integer k=0;k<150;k=k+1) begin
   @(negedge refclk);
   if(value!==old && value!==count) $fatal(1,"Torn CDC word %h old=%h new=%h",value,old,count);
  end
  if(value!==count) $fatal(1,"Handshake did not settle");
 end
 @(negedge pix);count=0;lock=0;
 repeat(150) @(negedge refclk);
 if(value!==0 || led[0] || led[3]) $fatal(1,"Reset snapshot or stale lock indication");
 @(negedge pix);pix_run=0;hpd=1;
 repeat(30) @(negedge refclk);
 if(source_hpd!==0 || led[1]!==0) $fatal(1,"HPD disconnect must work without pixel clock");
 hpd=0;repeat(30) @(negedge refclk);
 if(source_hpd!==1 || led[1]!==1) $fatal(1,"HPD connect must work without pixel clock");
 $display("PASS CDC: arbitrary 32-bit jumps including zero, coherent snapshots, lock gating, active-low board HPDN with absent pixel clock");$finish;
end
endmodule
