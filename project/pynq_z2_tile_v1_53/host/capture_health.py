"""Versioned board health; a working TCP socket is not a completed video frame."""
STATES=('WAIT_FIRST','HEALTHY','STALLED','INVALID_STREAM','DMA_ERROR','HALTED','RECOVERING','RECOVERY_FAILED')
MESSAGES=('网络在线，等待第一张完整图像','完整图像采集正常','完整帧采集已停滞，需检查输入或采集链路',
          'DMA 仍有完成记录，但没有新的有效图像','采集通道报告 DMA 或槽位错误','DMA 已停止，当前不能产生新图像','正在恢复采集，等待完整图像验证','采集恢复未完成，已停止新采集，需维护检查')
def decode_health(words,version=0x11300):
    if len(words)!=6 or words[0]!=0x484c5431 or words[1]>=(len(STATES) if version>=0x11400 else 6):
        raise ValueError('Invalid capture health schema')
    _,code,da,va,sr,cr=words
    if code==1 and (da>=500 or va>=500 or sr&0x771 or not cr&1):
        raise ValueError('Inconsistent healthy capture status')
    return dict(state=STATES[code],ready=code==1,dma_age_ms=da,
                valid_age_ms=None if va==0xffffffff else va,dma_status=sr,dma_control=cr,message=MESSAGES[code])
