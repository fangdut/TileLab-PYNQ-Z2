`timescale 1ns/1ps
module tb_color_correct;
 reg control_clk=0,pixel_clk=0,clock_enable=1;
 always #5 control_clk=~control_clk;
 always #7 if(clock_enable)pixel_clk=~pixel_clk;else pixel_clk=0;
 reg control_resetn=0,pixel_resetn=0,config_changed=0;
 reg [31:0] config_r=256,config_g=256,config_b=256;
 wire config_ready;reg [23:0] rgb=0;reg de=0,vs=0;
 wire [23:0] rgb_out;wire de_out,vs_out;
 video_color_correct dut(.*);
 reg checking=0;integer checked=0,rg=256,gg=256,bg=256,rb=0,gb=0,bb=0;
 reg [23:0] expected0=0,expected1=0;reg de0=0,de1=0,vs0=0,vs1=0;
 function automatic [7:0] reference(input integer value,gain,black);
  integer result;
  begin result=value>black?((value-black)*gain+128)/256:0;reference=result>255?255:result;end
 endfunction
 always @(posedge pixel_clk)begin
  if(!pixel_resetn)begin expected0=0;expected1=0;de0=0;de1=0;vs0=0;vs1=0;end
  else begin
   expected1=expected0;
   expected0={reference(rgb[23:16],rg,rb),reference(rgb[15:8],gg,gb),reference(rgb[7:0],bg,bb)};
   de1=de0;de0=de;vs1=vs0;vs0=vs;
  end
  #1;
  if(checking)begin
   if(rgb_out!==expected1||de_out!==de1||vs_out!==vs1)$fatal(1,"Color/DE/VS latency mismatch rgb=%h expected=%h",rgb_out,expected1);
   checked=checked+1;
  end
 end
 task pixels;
  integer i;
  begin
   for(i=0;i<260;i=i+1)begin
    @(negedge pixel_clk);rgb={8'(i),8'(255-i),8'(i*17)};de=i[0];vs=i==13||i==201;
   end
  end
 endtask
 task ready_check(input integer r_gain,g_gain,b_gain,r_black,g_black,b_black);
  begin
   wait(config_ready);rg=r_gain;gg=g_gain;bg=b_gain;rb=r_black;gb=g_black;bb=b_black;
   repeat(8)@(negedge pixel_clk);checking=1;pixels();checking=0;
  end
 endtask
 task burst_config(input [31:0] r,g,b);
  begin
   @(negedge control_clk);config_r=r;config_changed=1;
   @(negedge control_clk);config_g=g;
   @(negedge control_clk);config_b=b;
   @(negedge control_clk);config_changed=0;
   repeat(2)@(negedge control_clk);
   if(config_ready)$fatal(1,"Premature configuration completion");
  end
 endtask
 initial begin
  repeat(5)@(negedge control_clk);control_resetn=1;pixel_resetn=1;
  ready_check(256,256,256,0,0,0);
  burst_config(260,314,403);ready_check(260,314,403,0,0,0);
  burst_config(32'h0010012a,32'h000c0104,32'h00140193);ready_check(298,260,403,16,12,20);
  // Link loss resets only the pixel pipeline; its static calibration survives.
  @(negedge pixel_clk);pixel_resetn=0;repeat(4)@(negedge pixel_clk);pixel_resetn=1;
  ready_check(298,260,403,16,12,20);
  @(negedge pixel_clk);pixel_resetn=0;clock_enable=0;
  burst_config(300,320,400);repeat(80)@(negedge control_clk);
  if(config_ready)$fatal(1,"Configuration completed without a destination clock");
  clock_enable=1;pixel_resetn=1;ready_check(300,320,400,0,0,0);
  config_r=256;config_g=256;config_b=256;control_resetn=0;pixel_resetn=0;
  repeat(5)@(negedge control_clk);control_resetn=1;pixel_resetn=1;
  ready_check(256,256,256,0,0,0);
  if(checked<1500)$fatal(1,"Insufficient RGB coverage");
  $display("PL_COLOR_ALL_256_LEVELS_ATOMIC_CONFIG_SATURATION_TIMING_CLOCK_LOSS_PASS checked=%0d",checked);$finish;
 end
 initial begin #1000000;$fatal(1,"Color test watchdog");end
endmodule
