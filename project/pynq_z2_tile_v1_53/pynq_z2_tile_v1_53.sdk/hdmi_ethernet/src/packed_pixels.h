#ifndef TILE_PACKED_PIXELS_H
#define TILE_PACKED_PIXELS_H
/* Lossless transport only: N BGR triplets followed by ceil(N/8) mask bytes.
 * Mask bit i%8 describes pixel i. The canonical source is B,G,R,0-or-1;
 * reject noncanonical high bits instead of silently discarding information.
 * Destination must be 4-byte aligned. Each call consumes <= budget words.
 * Buffer ownership is identical to WORD_RLE: immutable until TCP completion. */
#include <stdint.h>
typedef struct {
 const uint32_t *src; uint8_t *dst;
 uint32_t words,pos,bytes;
 int done,failed;
} PackedPixels;
static inline uint32_t packed_size(uint32_t words){return words*3+(words+7)/8;}
static inline void packed_begin(PackedPixels *s,const uint32_t *src,uint32_t words,void *dst,uint32_t capacity){
 s->src=src;s->dst=(uint8_t*)dst;s->words=words;s->pos=0;s->bytes=0;s->failed=0;s->done=0;
 if(words>0x3fffffffu || ((uintptr_t)dst&3u)){s->done=s->failed=1;return;}
 s->bytes=packed_size(words);
 if(s->bytes>capacity){s->done=s->failed=1;return;}
 if(!words)s->done=1;
}
static inline int packed_feed(PackedPixels *s,const uint32_t *input,uint32_t budget){
 uint32_t p,n,v,m;uint8_t *masks;
 if(s->done)return 1;
 p=s->pos;n=s->words-p;masks=s->dst+3*s->words;
 if(n>budget)n=budget;
 while(n){
  if(!(p&3u) && n>=4){
   uint32_t a=input[0],b=input[1],c=input[2],d=input[3];
   uint32_t *out=(uint32_t*)(s->dst+3*p);
   if((a|b|c|d)&0xfe000000u){s->done=s->failed=1;return 1;}
   out[0]=(a&0xffffffu)|((b&255u)<<24);
   out[1]=((b>>8)&0xffffu)|((c&0xffffu)<<16);
   out[2]=((c>>16)&255u)|((d&0xffffffu)<<8);
   m=((a>>24)&1u)|((b>>23)&2u)|((c>>22)&4u)|((d>>21)&8u);
   if(p&4u)masks[p>>3]|=(uint8_t)(m<<4);else masks[p>>3]=(uint8_t)m;
   p+=4;input+=4;n-=4;
  }else{
   v=*input++;
   if(v&0xfe000000u){s->done=s->failed=1;return 1;}
   s->dst[3*p]=(uint8_t)v;s->dst[3*p+1]=(uint8_t)(v>>8);s->dst[3*p+2]=(uint8_t)(v>>16);
   if(!(p&7u))masks[p>>3]=0;
   masks[p>>3]|=(uint8_t)(((v>>24)&1u)<<(p&7u));p++;n--;
  }
 }
 s->pos=p;if(p==s->words)s->done=1;return s->done;
}
#endif
