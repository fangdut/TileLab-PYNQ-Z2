#ifndef TILE_DMA_RECOVERY_H
#define TILE_DMA_RECOVERY_H
#include <stdint.h>
#define TILE_RECOVERY_MAGIC 0x52454331u
#define TILE_RECOVERY_MAX 3u
#define TILE_RESET_TIMEOUT_MS 1000u
#define TILE_VERIFY_TIMEOUT_MS 3000u
enum {REC_RUNNING=0,REC_RESETTING,REC_VERIFYING,REC_FAILED};
enum {REC_REASON_NONE=0,REC_REASON_HALTED,REC_REASON_DMA_ERROR,
      REC_REASON_RESET_TIMEOUT,REC_REASON_NO_SLOTS,REC_REASON_VERIFY_TIMEOUT,
      REC_REASON_REPEAT_DMA_ERROR,REC_REASON_BUDGET};
typedef struct {
 uint32_t state,attempts,successes,failures,reason,last_status;
 uint32_t interrupted,discarded,wait_product,good,duration_ms;
 uint64_t began,deadline,verified_at;
} TileDmaRecovery;
static inline unsigned recovery_begin(TileDmaRecovery *r,uint64_t now,uint64_t ticks_ms,
                                      uint32_t reason,uint32_t status){
 if(r->state!=REC_RUNNING)return 0;
 r->began=now;r->last_status=status;r->good=0;r->wait_product=1;
 if(r->attempts>=TILE_RECOVERY_MAX){r->state=REC_FAILED;r->reason=REC_REASON_BUDGET;r->failures++;r->duration_ms=0;return 0;}
 r->attempts++;r->reason=reason;r->state=REC_RESETTING;r->deadline=now+TILE_RESET_TIMEOUT_MS*ticks_ms;return 1;
}
static inline void recovery_failed(TileDmaRecovery *r,uint64_t now,uint64_t ticks_ms,uint32_t reason){
 r->state=REC_FAILED;r->reason=reason;r->failures++;r->good=0;
 r->duration_ms=(uint32_t)((now-r->began)/ticks_ms);
}
static inline void recovery_verifying(TileDmaRecovery *r,uint64_t now,uint64_t ticks_ms){
 r->state=REC_VERIFYING;r->good=0;r->verified_at=0;r->deadline=now+TILE_VERIFY_TIMEOUT_MS*ticks_ms;
}
static inline void recovery_good(TileDmaRecovery *r,uint64_t now){if(r->state==REC_VERIFYING && r->good<2){r->good++;if(r->good==2)r->verified_at=now;}}
static inline void recovery_bad(TileDmaRecovery *r){if(r->state==REC_VERIFYING){r->good=0;r->verified_at=0;r->discarded++;}}
static inline void recovery_success(TileDmaRecovery *r,uint64_t now,uint64_t ticks_ms){
 r->state=REC_RUNNING;r->successes++;r->duration_ms=(uint32_t)((now-r->began)/ticks_ms);
}
static inline void recovery_snapshot(const TileDmaRecovery *r,uint32_t out[14]){
 out[0]=TILE_RECOVERY_MAGIC;out[1]=r->state;out[2]=r->attempts;out[3]=r->successes;
 out[4]=r->failures;out[5]=r->reason;out[6]=r->last_status;out[7]=r->interrupted;
 out[8]=r->discarded;out[9]=r->wait_product;out[10]=TILE_RECOVERY_MAX;
 out[11]=TILE_RESET_TIMEOUT_MS;out[12]=TILE_VERIFY_TIMEOUT_MS;out[13]=r->duration_ms;
}
#endif
