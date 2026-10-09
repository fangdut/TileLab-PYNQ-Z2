#ifndef TILE_RLE_PROBE_H
#define TILE_RLE_PROBE_H
#include <stdint.h>
#include <string.h>
/* Only choose a wire encoding; never classify pixels or affect PL decisions.
 * Read 64 dispersed blocks (4 KiB total). Require half of adjacent pairs to
 * repeat. A wrong estimate only misses savings or costs encoding time; the
 * full encoder still enforces bounds, exactness and its 5% savings floor. */
static inline unsigned tile_rle_worthwhile(const uint32_t *pixels,unsigned words){
 uint32_t block[16];unsigned i,k,offset,repeats=0;
 if(words<16)return 0;
 for(i=0;i<64;i++){
  offset=((i*15317u+9011u)%(words-15u))&~7u;
  memcpy(block,pixels+offset,sizeof(block));
  for(k=1;k<16;k++)if(block[k]==block[k-1])repeats++;
 }
 return repeats>=480;
}
#endif
