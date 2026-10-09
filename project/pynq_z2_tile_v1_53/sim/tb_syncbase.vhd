library ieee;
use ieee.std_logic_1164.all;
use std.env.all;
entity tb_syncbase is end;
architecture test of tb_syncbase is
 signal ic:std_logic:='0'; signal oc:std_logic:='0';
 signal rst:std_logic:='1';signal din:std_logic:='0';signal dout:std_logic;
begin
 ic<=not ic after 2.5 ns;oc<=not oc after 6.734 ns;
 dut:entity work.SyncBase port map(aReset=>rst,InClk=>ic,iIn=>din,OutClk=>oc,oOut=>dout);
 process begin
  for i in 0 to 15 loop
   rst<='1';din<='1';wait for 17 ns;
   assert dout='0' report "reset assertion failed" severity failure;
   wait for i*1 ns;rst<='0';wait for 100 ns;
   assert dout='1' report "synchronized release/data transfer failed" severity failure;
   din<='0';wait for 80 ns;
   assert dout='0' report "data deassertion failed" severity failure;
  end loop;
  report "PASS RX RESET: asynchronous phases, reset assertion and synchronized data recovery" severity note;
  finish;
 end process;
end;
