#ifndef TILE_DESCRIPTOR_CRC_H
#define TILE_DESCRIPTOR_CRC_H
#include <stdint.h>
/* Validate the 40 raw PL trailer words before ARM replaces magic, pointer,
 * reason, boot ID, timestamp, or product-complete flags. Word 8 is defined
 * as zero for CRC calculation and carries the received CRC on the wire. */
static inline uint32_t tile_descriptor_crc(const uint32_t words[40]){
 uint32_t crc=0xffffffffu;unsigned i,bit;
 for(i=0;i<40;i++){
  crc^=i==8?0u:words[i];
  for(bit=0;bit<32;bit++)crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);
 }
 return ~crc;
}
#endif
