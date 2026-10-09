#ifndef TILE_EVENT_IDENTITY_H
#define TILE_EVENT_IDENTITY_H
#include <stdint.h>
/* V1.32 ARM event word 8: low byte reason, upper 24 bits acquisition recovery
 * generation. This is written only after verification of the original PL CRC.
 * The generation is bound when pixels are consumed, never at network send. */
static inline uint32_t tile_event_identity(uint32_t generation,uint32_t reason){
 return (generation<<8)|(reason&255u);
}
static inline uint32_t tile_event_with_reason(uint32_t identity,uint32_t reason){
 return (identity&0xffffff00u)|(reason&255u);
}
#endif
