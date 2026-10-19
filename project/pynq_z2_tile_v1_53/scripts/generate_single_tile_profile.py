from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'host'))
from single_tile_profile import load,roi_words
def render(p):
    lo,hi=roi_words(p);return '''/* Generated from config/single_tile.json; no image inference in ARM. */
#ifndef TILE_SINGLE_PROFILE_H
#define TILE_SINGLE_PROFILE_H
#define TILE_SINGLE_PROFILE_ID 0x%08xu
#define TILE_SINGLE_FIRMWARE_VERSION 0x%08xu
#define TILE_SINGLE_ROI_MIN 0x%08xu
#define TILE_SINGLE_ROI_MAX 0x%08xu
#define TILE_SINGLE_SIDE 500u
#define TILE_SINGLE_CONFIG_MASK 0x7fffffffu
#define TILE_SINGLE_CONFIG_WORD 0x7bf35a07u
#endif
'''%(p['profile_id'],p['firmware_version'],lo,hi)
def main():
    p=load(ROOT);dest=ROOT/'pynq_z2_tile_v1_53.sdk/ethernet_sources/single_tile_profile.h';dest.write_text(render(p));print(hex(p['profile_id']))
if __name__=='__main__':main()
