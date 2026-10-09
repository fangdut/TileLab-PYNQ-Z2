#include <assert.h>
#include <stdio.h>
#include "event_queue.h"
int main(void){
 uint32_t meta[64],desc[QUEUE_CAPACITY*DESC_WORDS],words[DESC_WORDS]={0};EventQueue q;unsigned i;
 queue_init(&q,meta,desc,7);assert(meta[M_MAGIC]==TILE_MAGIC && meta[M_BOOT]==7);
 assert(queue_trigger(&q,1)==1);for(i=0;i<80;i++)assert(queue_trigger(&q,1)==0);
 assert(!queue_trigger(&q,0));assert(!queue_trigger(&q,0));assert(!queue_trigger(&q,1));
 for(i=0;i<3;i++)queue_trigger(&q,0);assert(queue_trigger(&q,1)==1);
 for(i=0;i<QUEUE_CAPACITY;i++){
  unsigned s=queue_free_slot(&q);assert(s==i);words[1]=FRAME_BASE+s*FRAME_STRIDE;words[2]=100+i;
  assert(queue_publish(&q,s,words));assert(desc[i*DESC_WORDS]==i+1);
 }
 assert(queue_free_slot(&q)==QUEUE_CAPACITY && meta[M_DEPTH]==QUEUE_CAPACITY);
 assert(!queue_publish(&q,QUEUE_CAPACITY,words));
 meta[M_ACK]=3;queue_ack(&q);assert(meta[M_ACK_ERRORS]==1 && meta[M_DEPTH]==12);
 meta[M_ACK]=1;queue_ack(&q);assert(meta[M_DEPTH]==11 && queue_free_slot(&q)==0);
 queue_ack(&q);assert(meta[M_DEPTH]==11);
 for(i=2;i<=QUEUE_CAPACITY;i++){meta[M_ACK]=i;queue_ack(&q);}assert(meta[M_DEPTH]==0 && q.slot_used==0);
 for(i=0;i<10000;i++){
  unsigned s=queue_free_slot(&q);words[1]=FRAME_BASE+s*FRAME_STRIDE;words[2]=1000+i;
  assert(queue_publish(&q,s,words));meta[M_ACK]=q.tail;queue_ack(&q);assert(meta[M_DEPTH]==0);
 }
 puts("EVENT QUEUE PASS: debounce, twelve retained slots, full backpressure, wrong ACK, idempotent ACK and 10000 wraps");return 0;
}
