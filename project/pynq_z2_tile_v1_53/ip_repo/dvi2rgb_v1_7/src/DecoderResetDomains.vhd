-- TileLab V1.31: one asynchronous-assert/synchronous-release reset per domain.
-- Raw MMCM lock feeds only the pixel reset bridge. All three decoder timeout
-- channels share the same reference-domain reset; they do not resynchronize it
-- independently. PixelReady may assert only after the pixel reset releases.
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity DecoderResetDomains is
  port (aLocked : in std_logic; PixelClk : in std_logic; RefClk : in std_logic;
        pReset : out std_logic; rReset : out std_logic; PixelReady : out std_logic);
end DecoderResetDomains;

architecture Behavioral of DecoderResetDomains is
  signal pReset_int : std_logic;
begin
  PixelResetBridge: entity work.ResetBridge
    generic map (kPolarity => '1')
    port map (aRst => not aLocked, OutClk => PixelClk, oRst => pReset_int);
  ReferenceResetBridge: entity work.ResetBridge
    generic map (kPolarity => '1')
    port map (aRst => pReset_int, OutClk => RefClk, oRst => rReset);
  pReset <= pReset_int;
  PixelReady <= not pReset_int;
end Behavioral;
