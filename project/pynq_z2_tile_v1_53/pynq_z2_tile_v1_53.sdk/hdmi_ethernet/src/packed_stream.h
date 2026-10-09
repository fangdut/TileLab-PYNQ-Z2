#ifndef TILE_PACKED_STREAM_H
#define TILE_PACKED_STREAM_H
#include <stdint.h>
#include "packed_pixels.h"
/* Only the completed immutable BGR prefix may be passed to lwIP while the
 * mask plane is still being assembled. Fail closed on inconsistent state. */
static inline uint32_t packed_stream_ready(uint32_t header_bytes,uint32_t words,uint32_t produced,int done,int failed){
 uint32_t body;
 if(failed || words>0x3fffffffu || produced>words || (done && produced!=words))return 0;
 body=packed_size(words);if(header_bytes>0xffffffffu-body)return 0;
 return header_bytes+(done?body:3*produced);
}
/* One failed pinned image only. A retry must preserve all original bits in
 * RAW32 so the receiver can report the original PL CRC failure. A different
 * image clears the fallback instead of poisoning later frame-slot reuse. */
typedef struct {uint32_t valid,boot,event,frame,slot,crc;} PackedFailure;
static inline void packed_failure_set(PackedFailure *s,uint32_t boot,const volatile uint32_t *d,uint32_t crc){
 s->boot=boot;s->event=d[0];s->slot=d[1];s->frame=d[2];s->crc=crc;s->valid=1;
}
static inline int packed_failure_matches(PackedFailure *s,uint32_t boot,const volatile uint32_t *d,uint32_t crc){
 if(s->valid && s->boot==boot && s->event==d[0] && s->slot==d[1] && s->frame==d[2] && s->crc==crc)return 1;
 s->valid=0;return 0;
}
#endif
