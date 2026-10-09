library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
use std.env.all;

entity tb_decoder_resets is end;
architecture Test of tb_decoder_resets is
  signal pclk,rclk : std_logic := '0';
  signal p_run,r_run : boolean := true;
  signal locked : std_logic := '0';
  signal pr,rr,ready : std_logic;
  signal rdata,pdata : std_logic_vector(2 downto 0) := (others=>'0');
  signal po,ro : std_logic_vector(2 downto 0);
begin
  process begin wait for 6.734 ns; if p_run then pclk<=not pclk; else pclk<='0'; end if; end process;
  process begin wait for 2.5 ns; if r_run then rclk<=not rclk; else rclk<='0'; end if; end process;
  dut: entity work.DecoderResetDomains
    port map(aLocked=>locked,PixelClk=>pclk,RefClk=>rclk,pReset=>pr,rReset=>rr,PixelReady=>ready);
  channels: for n in 0 to 2 generate
    overflow_to_pixel: entity work.SyncBase
      generic map(kResetTo=>'0',kStages=>2)
      port map(iReset=>rr,oReset=>pr,InClk=>rclk,iIn=>rdata(n),OutClk=>pclk,oOut=>po(n));
    request_to_ref: entity work.SyncBase
      generic map(kResetTo=>'1',kStages=>2)
      port map(iReset=>pr,oReset=>rr,InClk=>pclk,iIn=>pdata(n),OutClk=>rclk,oOut=>ro(n));
  end generate;
  -- Digital simulation cannot model analog metastability. These checks verify
  -- release phase, clock-stop behavior, reset values, and six real crossings.
  process(pr) begin
    if falling_edge(pr) then assert pclk='1' and pclk'last_event=0 ns report "Pixel reset released away from target edge" severity failure; end if;
  end process;
  process(rr) begin
    if falling_edge(rr) then assert rclk='1' and rclk'last_event=0 ns report "Reference reset released away from target edge" severity failure; end if;
  end process;
  process
    variable checks : natural := 0;
    procedure check_asserted is
    begin
      wait for 1 ns;
      assert pr='1' and rr='1' and ready='0' report "Asynchronous assertion or ready gating failed" severity failure;
      assert po="000" and ro="111" report "Crossing reset values are inconsistent" severity failure;
      checks:=checks+1;
    end procedure;
    procedure check_running is
    begin
      wait for 100 ns;
      assert pr='0' and rr='0' and ready='1' report "Reset did not release with running clocks" severity failure;
      assert po=rdata and ro=pdata report "Shared reset changed stable transferred data" severity failure;
      checks:=checks+1;
    end procedure;
  begin
    check_asserted;
    locked<='1';check_running;
    -- Sweep assertion/deassertion phases with differing payloads on all channels.
    for n in 0 to 63 loop
      wait for (41+((n*337) mod 7000))*1 ps;
      locked<='0';check_asserted;wait for 7300 ps;
      rdata<=std_logic_vector(to_unsigned(n mod 8,3));pdata<=std_logic_vector(to_unsigned((n+3) mod 8,3));
      locked<='1';check_running;
    end loop;
    -- Pixel clock absent: even a renewed raw lock must not release pixel reset.
    locked<='0';p_run<=false;check_asserted;wait for 30 ns;
    locked<='1';wait for 70 ns;
    assert pr='1' and rr='1' and ready='0' report "Ready asserted without a pixel clock" severity failure;
    p_run<=true;check_running;
    -- Reference clock absent: it stays reset while the live pixel domain recovers.
    locked<='0';r_run<=false;check_asserted;wait for 30 ns;
    locked<='1';wait for 70 ns;
    assert pr='0' and ready='1' and rr='1' and ro="111" report "Stopped reference domain released reset" severity failure;
    r_run<=true;check_running;
    -- Reassert lock loss while BOTH clocks are absent; outputs must still reset.
    p_run<=false;r_run<=false;wait for 30 ns;locked<='0';check_asserted;
    locked<='1';wait for 70 ns;
    assert pr='1' and rr='1' and ready='0' report "Stopped domains released reset" severity failure;
    p_run<=true;r_run<=true;check_running;
    report "PASS V131 decoder resets: 64 phase sweeps, 3 stopped-clock scenarios, 6 crossings, checks=" & integer'image(checks) severity note;
    finish;
  end process;
  process begin wait for 25 us; assert false report "Reset test timeout" severity failure; end process;
end Test;
