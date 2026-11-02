`timescale 1ns/1ps
module tb_hpd;
 reg clk=0;always #5 clk=~clk;
 reg resetn=0;wire hpd;
 hdmi_hpd_startup #(.STARTUP_CYCLES(7)) dut(clk,resetn,hpd);
 task startup;
  begin
   @(negedge clk);resetn=1;
   repeat(6)begin @(posedge clk);#1;if(hpd)$fatal(1,"HPD asserted before DDC startup delay");end
   @(posedge clk);#1;if(!hpd)$fatal(1,"HPD startup delay did not end");
   repeat(30)begin @(posedge clk);#1;if(!hpd)$fatal(1,"HPD dropped after startup");end
  end
 endtask
 initial begin
  repeat(3)@(negedge clk);startup();
  #2;resetn=0;#1;if(hpd)$fatal(1,"HPD did not fall immediately on reset");
  repeat(4)@(negedge clk);startup();
  $display("HDMI_HPD_DELAY_SATURATION_ASYNC_RESET_PASS");$finish;
 end
endmodule
