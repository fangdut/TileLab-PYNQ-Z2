#ifndef TILE_EVENT_QUEUE_H
#define TILE_EVENT_QUEUE_H
#include <stdint.h>
#define QUEUE_CAPACITY 12u
#define DESC_WORDS 40u
#define FRAME_BYTES 3686400u
#define FRAME_BASE 0x10100000u
#define FRAME_STRIDE 0x00400000u
#define FRAME_SLOTS 48u
#define TILE_MAGIC 0x54494c33u
#define M_DETECT_MODE_REQUEST 61u /* 0: two passes, 1: high only, 2: four passes */
#define M_DETECT_MODE_APPLIED 62u
/* Legacy diagnostics retain their 0/1 interpretation for old modes. */
#define M_WEAK_DISABLE_REQUEST M_DETECT_MODE_REQUEST
#define M_WEAK_DISABLE_APPLIED M_DETECT_MODE_APPLIED
#define M_DESC_CRC_ERRORS 37u
#define M_DESC_VERIFIED 38u
#define M_LAST_DESC_CRC 39u
/* These two extra DDR words are for the JTAG reader. The existing 64-word
 * status layout and the 276-byte TCP header remain unchanged. */
#define M_QUEUE_READ_POS 64u
#define M_QUEUE_WRITE_POS 65u
#define M_HEALTH_BASE 66u
#define M_RECOVERY_BASE 72u
/* Append-only JTAG diagnostics. Captured/applied TCP state remains config bit 26. */
#define M_PRODUCT_GATE_REQUEST 86u /* 0: legacy weighted brightness 320, 1: 160 */
#define M_PRODUCT_GATE_APPLIED 87u
#define M_WIDE_WEAK_REQUEST 88u /* zero=radius-8 only, one=radius-8/16 weak support */
#define M_WIDE_WEAK_APPLIED 89u
#define META_WORDS 90u
enum {M_MAGIC,M_VERSION,M_BOOT,M_HEARTBEAT,M_HEAD,M_TAIL,M_DEPTH,M_EVENTS,M_DROPPED,M_CAPTURED,M_INVALID,M_ACK,M_REQUEST,M_REASON,M_REQUEST_ACK,M_THRESHOLD,M_ENABLE,M_GAPS,M_FRAMES,M_LAST_SEQ,M_ACTIVE,M_CONFIG,M_ERRORS,M_ACK_ERRORS};
typedef struct {volatile uint32_t *meta,*desc;uint64_t slot_used;uint32_t head,tail,last_ack,incident,quiet;unsigned read_pos,write_pos;unsigned char refs[FRAME_SLOTS];} EventQueue;
static inline volatile uint32_t *queue_front(const EventQueue *q){return q->desc+q->read_pos*DESC_WORDS;}
static inline void queue_barrier(void){
#ifdef __arm__
 __asm__ volatile("dmb sy" ::: "memory");
#endif
}
static inline void queue_init(EventQueue *q,volatile uint32_t *m,volatile uint32_t *d,uint32_t boot){
 unsigned i;q->meta=m;q->desc=d;q->slot_used=0;q->head=q->tail=q->last_ack=q->incident=q->quiet=0;
 q->read_pos=q->write_pos=0;
 for(i=0;i<META_WORDS;i++){m[i]=0;}
 for(i=0;i<FRAME_SLOTS;i++)q->refs[i]=0;
 for(i=0;i<QUEUE_CAPACITY*DESC_WORDS;i++){d[i]=0;}
 m[M_VERSION]=0x00012b00u;m[M_BOOT]=boot;m[M_THRESHOLD]=36;m[M_ENABLE]=0;queue_barrier();m[M_MAGIC]=TILE_MAGIC;
}
static inline void queue_reject_ack(EventQueue *q){
 /* Consume a rejected mailbox request without remembering a future event.
  * Returning the mailbox to the committed head also prevents an old invalid
  * write from releasing a frame which is published later. A new ACK write is
  * required. The single-threaded network path calls this before replying. */
 q->meta[M_ACK_ERRORS]++;q->last_ack=q->head;
 q->meta[M_ACK]=q->head;queue_barrier();
}
static inline void queue_ack(EventQueue *q){
 /* Zero is a valid event after UINT32_MAX. Initial and duplicate requests
  * are already handled by last_ack; do not reserve a protocol sequence. */
 uint32_t a=q->meta[M_ACK];if(a==q->last_ack)return;
 if(q->head!=q->tail && a==q->head+1){
  volatile uint32_t *d=queue_front(q);
  uint32_t slot=(d[1]-FRAME_BASE)/FRAME_STRIDE;
  if(slot>=FRAME_SLOTS || !q->refs[slot]){queue_reject_ack(q);return;}
  if(--q->refs[slot]==0){q->slot_used&=~(1ULL<<slot);}
  d[0]=0;q->head++;q->last_ack=a;if(++q->read_pos==QUEUE_CAPACITY)q->read_pos=0;
  q->meta[M_QUEUE_READ_POS]=q->read_pos;queue_barrier();
  q->meta[M_HEAD]=q->head;q->meta[M_DEPTH]=q->tail-q->head;
 }else queue_reject_ack(q);
}
static inline unsigned queue_free_slot(const EventQueue *q){
 unsigned i;for(i=0;i<QUEUE_CAPACITY;i++)if(!(q->slot_used&(1u<<i)))return i;
 return QUEUE_CAPACITY;
}
static inline unsigned queue_trigger(EventQueue *q,unsigned alarm){
 if(alarm){unsigned trigger=!q->incident;q->incident=1;q->quiet=0;if(trigger)q->meta[M_EVENTS]++;return trigger;}
 if(q->quiet<3){q->quiet++;}
 if(q->quiet>=3){q->incident=0;}
 return 0;
}
static inline unsigned queue_publish(EventQueue *q,unsigned slot,const uint32_t words[DESC_WORDS]){
 unsigned i;volatile uint32_t *d;
 if(slot>=FRAME_SLOTS || q->tail-q->head>=QUEUE_CAPACITY)return 0;
 d=q->desc+q->write_pos*DESC_WORDS;
 for(i=1;i<DESC_WORDS;i++){d[i]=words[i];}
 q->slot_used|=1ULL<<slot;q->refs[slot]++;
 queue_barrier();d[0]=q->tail+1;queue_barrier();q->tail++;
 if(++q->write_pos==QUEUE_CAPACITY)q->write_pos=0;
 q->meta[M_QUEUE_WRITE_POS]=q->write_pos;queue_barrier();
 q->meta[M_TAIL]=q->tail;q->meta[M_DEPTH]=q->tail-q->head;return 1;
}
#endif
