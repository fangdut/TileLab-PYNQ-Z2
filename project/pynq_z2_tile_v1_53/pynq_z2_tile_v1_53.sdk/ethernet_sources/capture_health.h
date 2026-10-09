#ifndef TILE_CAPTURE_HEALTH_H
#define TILE_CAPTURE_HEALTH_H
#include <stdint.h>
/* Diagnostic only: no DMA reset, ownership change, or vision processing. */
#define TILE_HEALTH_MAGIC 0x484c5431u
#define TILE_HEALTH_TIMEOUT_MS 500u
enum { TILE_HEALTH_WAIT=0,TILE_HEALTH_OK,TILE_HEALTH_STALLED,
       TILE_HEALTH_INVALID,TILE_HEALTH_DMA_ERROR,TILE_HEALTH_HALTED };
typedef struct {uint64_t started,done,valid,published;unsigned seen_done,seen_valid;} CaptureHealth;
static inline void health_start(CaptureHealth *h,uint64_t now){
 h->started=h->done=h->valid=h->published=now;h->seen_done=h->seen_valid=0;
}
static inline uint32_t health_age(uint64_t now,uint64_t then,uint64_t ticks_per_ms){
 uint64_t age=(now-then)/ticks_per_ms;
 return age>=UINT32_MAX?UINT32_MAX-1:(uint32_t)age;
}
static inline void health_snapshot(const CaptureHealth *h,uint64_t now,uint64_t ticks_per_ms,
                                   uint32_t sr,uint32_t cr,uint32_t software_error,uint32_t out[6]){
 uint32_t da=health_age(now,h->done,ticks_per_ms);
 uint32_t va=h->seen_valid?health_age(now,h->valid,ticks_per_ms):UINT32_MAX;
 uint32_t state=TILE_HEALTH_OK;
 if((sr&0x770u)||software_error)state=TILE_HEALTH_DMA_ERROR;
 else if(!(cr&1u)||(sr&1u))state=TILE_HEALTH_HALTED;
 else if(!h->seen_done)state=TILE_HEALTH_WAIT;
 else if(da>=TILE_HEALTH_TIMEOUT_MS)state=TILE_HEALTH_STALLED;
 else if((!h->seen_valid && health_age(now,h->started,ticks_per_ms)>=TILE_HEALTH_TIMEOUT_MS) ||
         (h->seen_valid && va>=TILE_HEALTH_TIMEOUT_MS))state=TILE_HEALTH_INVALID;
 else if(!h->seen_valid)state=TILE_HEALTH_WAIT;
 out[0]=TILE_HEALTH_MAGIC;out[1]=state;out[2]=da;out[3]=va;out[4]=sr;out[5]=cr;
}
#endif
