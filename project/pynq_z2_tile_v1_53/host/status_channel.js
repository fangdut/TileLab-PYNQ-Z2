/* One outstanding browser fetch per channel; invalidated replies never publish.
 * Archive and live channels are independent. Abort does not cancel server disk
 * work: /api/archive separately refuses concurrent waiters under the Records lock.
 */
class StatusChannel {
 constructor(onValue,onError,{timeout=5000}={}){this.onValue=onValue;this.onError=onError;this.timeout=timeout;this.active=null;this.epoch=0}
 invalidate(){this.epoch++;if(this.active)this.active.controller.abort();this.active=null}
 poll(url,context){
  if(this.active)return this.active.promise;
  const token={epoch:this.epoch,controller:new AbortController()};this.active=token;
  const current=()=>this.active===token&&this.epoch===token.epoch;
  const timer=setTimeout(()=>token.controller.abort(),this.timeout);
  token.promise=(async()=>{
   try{
    const response=await fetch(url,{cache:'no-store',signal:token.controller.signal});
    const value=await response.json();
    if(!response.ok)throw Error(value.error||'状态读取失败');
    if(current())this.onValue(value,context);
   }catch(error){if(current())this.onError(error.name==='AbortError'?Error('刷新超时，等待重试'):error)}
   finally{clearTimeout(timer);if(current())this.active=null}
  })();return token.promise;
 }
}
if(typeof module!=='undefined')module.exports={StatusChannel};
