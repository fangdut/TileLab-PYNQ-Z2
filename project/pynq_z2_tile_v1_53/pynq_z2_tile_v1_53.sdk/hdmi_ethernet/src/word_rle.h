#ifndef TILE_WORD_RLE_H
#define TILE_WORD_RLE_H
/* Lossless transport encoding, not image analysis. Each tag counts 32-bit
 * pixels: bit31=repeat (one value follows), otherwise literal values follow.
 * Caller owns/pins source and destination until all TCP references are gone.
 * Incremental steps bound acquisition-loop work. Overflow chooses raw mode. */
#include <stdint.h>
#define RLE_NONE 0xffffffffu
typedef struct {
 const uint32_t *src; uint32_t *dst;
 uint32_t words,capacity,pos,out,value,count,literal_tag,literal_count;
 int done,failed;
} WordRle;
static inline void rle_begin(WordRle *s,const uint32_t *src,uint32_t words,uint32_t *dst,uint32_t capacity){
 s->src=src;s->dst=dst;s->words=words;s->capacity=capacity;s->pos=s->out=s->count=s->literal_count=0;
 s->literal_tag=RLE_NONE;s->value=0;s->done=s->failed=0;
}
static inline void rle_close_literal(WordRle *s){
 if(s->literal_tag!=RLE_NONE){s->dst[s->literal_tag]=s->literal_count;s->literal_tag=RLE_NONE;s->literal_count=0;}
}
static inline int rle_emit(WordRle *s){
 uint32_t i,need;
 if(!s->count)return 1;
 need=s->count>=3?2:s->count+(s->literal_tag==RLE_NONE);
 if(need>s->capacity-s->out){s->failed=1;s->done=1;return 0;}
 if(s->count>=3){
  rle_close_literal(s);s->dst[s->out++]=0x80000000u|s->count;s->dst[s->out++]=s->value;
 }else{
  if(s->literal_tag==RLE_NONE){s->literal_tag=s->out++;s->dst[s->literal_tag]=0;}
  for(i=0;i<s->count;i++)s->dst[s->out++]=s->value;
  s->literal_count+=s->count;
 }
 s->count=0;return 1;
}
static inline int rle_feed(WordRle *s,const uint32_t *input,uint32_t budget){
 uint32_t value;
 if(s->done)return 1;
 while(budget-- && s->pos<s->words){
  value=*input++;s->pos++;
  if(s->count && value!=s->value && !rle_emit(s))return 1;
  s->value=value;s->count++;
 }
 if(s->pos==s->words){if(!rle_emit(s))return 1;rle_close_literal(s);s->done=1;}
 return s->done;
}
static inline int rle_step(WordRle *s,uint32_t budget){return rle_feed(s,s->src+s->pos,budget);}
#endif
