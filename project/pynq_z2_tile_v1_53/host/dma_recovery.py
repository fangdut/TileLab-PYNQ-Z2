"""Versioned diagnostics for bounded DMA recovery, not pixel processing."""
STATES=('RUNNING','RESETTING','VERIFYING','FAILED')
REASONS=('尚无恢复','DMA 停止','DMA 报错','复位等待超时','可用帧槽不足',
         '完整帧验证超时','验证期间 DMA 再次异常','本次启动的恢复次数已用完')
def decode_recovery(words):
    if len(words)!=14 or words[0]!=0x52454331 or words[1]>=len(STATES) or words[5]>=len(REASONS):
        raise ValueError('Invalid DMA recovery schema')
    _,state,attempts,successes,failures,reason,status,interrupted,discarded,waiting,limit,reset_ms,verify_ms,duration=words
    if waiting not in (0,1) or limit!=3 or attempts>limit or successes>attempts or reset_ms!=1000 or verify_ms!=3000:
        raise ValueError('Inconsistent DMA recovery limits')
    return dict(state=STATES[state],attempts=attempts,successes=successes,failures=failures,
                reason=REASONS[reason],reason_code=reason,last_dma_status=status,
                interrupted_product_observations=interrupted,discarded_packets=discarded,
                waiting_new_product=bool(waiting),max_attempts=limit,
                reset_timeout_ms=reset_ms,verify_timeout_ms=verify_ms,last_duration_ms=duration)
