#ifndef TILE_HEADER_CRC_H
#define TILE_HEADER_CRC_H
#include <stdint.h>
#include <stddef.h>
/* Protocol words are little endian on this Cortex-A9. Only the 272-byte
 * response header is scanned here; full image CRC remains a PL operation. */
static inline uint32_t tile_header_crc(const uint32_t *words,size_t count){
 uint32_t crc=0xffffffffu;size_t i;unsigned bit;
 for(i=0;i<count;i++){
  crc^=words[i];
  for(bit=0;bit<32;bit++)crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);
 }
 return ~crc;
}
#endif
