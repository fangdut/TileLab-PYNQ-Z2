from pathlib import Path
p=Path(__file__).resolve().parents[1]/'host/workstation.html';s=p.read_text(encoding='utf-8')
s=s.replace('<div class="preview-tag">HDMI → FPGA 多区域检测 → 事件队列 → 复核</div>','<div class="preview-tag" id="previewIdentity" role="status">等待开发板画面</div>')
s=s.replace("s.busy||recovering||s.pending_confirmation","s.busy||recovering||!!s.pending_operation")
start=s.index('if(s.frame){const f=s.frame;')
end=s.index('\nrenderCards();',start)
s=s[:start]+'''if(s.frame){const f=s.frame;const key=f.frame_id+'_'+f.acquired_at;if(key!==lastFrame){lastFrame=key;Promise.all([loadImage('/api/image?frame='+encodeURIComponent(key)),loadImage('/api/image?mask=1&frame='+encodeURIComponent(key))]).then(([a,b])=>{if(key!==lastFrame)return;liveFrame=f;liveImage=a;maskImage=b;paintLive()}).catch(()=>{if(key===lastFrame){lastFrame='';toast('图像更新未完成，正在重新获取对应帧')}})}}
updatePreviewIdentity();'''+s[end:]
needle="function paintLive(){draw("
assert s.count(needle)==1
s=s.replace(needle,"function paintLive(){updatePreviewMetadata();draw(")
idx=s.index('function paintLive()')
s=s[:idx]+'''function updatePreviewMetadata(){if(!liveFrame)return;const f=liveFrame;$('empty').classList.add('hidden');$('verdict').className='chip '+(f.alarm?'bad':'ok');$('verdict').textContent=f.alarm?'候选异常 · 需复核':'本帧未触发候选';$('frameId').textContent=f.frame_id;$('productId').textContent=f.product_id||'—';$('area').textContent=f.candidate_pixels.toLocaleString();$('duration').textContent=(f.transfer_ms/1000).toFixed(2)+' 秒';$('live').dataset.frameKey=f.frame_id+'_'+f.acquired_at;updatePreviewIdentity()}
function updatePreviewIdentity(){if(!liveFrame)return;const age=Math.max(0,(Date.now()-Date.parse(liveFrame.acquired_at))/1000);const held=state?.preview_stale||age>2;const kind=liveFrame.selection==='FPGA_PRODUCT_BEST_FRAME'?'产品最佳证据帧':'实时抽样帧';$('previewIdentity').textContent=(held?'保留画面 · 非当前实时 / ':'')+kind+' · 帧 '+liveFrame.frame_id;$('previewIdentity').style.borderColor=held?'#e1ad62':'#4d6b70';$('frameText').textContent=`主机接收 ${formatTime(liveFrame.acquired_at)} · ${age.toFixed(1)} 秒前；图像、红框、帧号同步显示`}
'''+s[idx:]
# A local-service outage must visibly mark the retained image too.
s=s.replace("$('connection').textContent='本地服务未连接'","$('connection').textContent='本地服务未连接';if(state)state.preview_stale=true;updatePreviewIdentity()")
p.write_text(s,encoding='utf-8')
print('Preview metadata now commits together with its image/mask pair')
