// A closed or superseded review cannot consume a late image response.
class ReviewSession {
  constructor(){this.epoch=0;this.token=null;this.controller=null;this.verified=false;this.revision=null;}
  begin(id){
    if(typeof id!=='string'||!id)throw Error('Missing review identity');
    this.close();this.controller=new AbortController();
    this.token=Object.freeze({id,epoch:this.epoch,signal:this.controller.signal});
    return this.token;
  }
  isCurrent(token){return !!token&&this.token===token&&!token.signal.aborted;}
  bindRevision(token,value){
    if(!this.isCurrent(token))return false;
    if(!Number.isSafeInteger(value)||value<0)throw Error('缺少有效复核修订号');
    if(this.revision!==null)throw Error('不能替换已打开记录的修订号');
    this.revision=value;return true;
  }
  complete(token){if(!this.isCurrent(token))return false;this.verified=true;return true;}
  fail(token){if(!this.isCurrent(token))return false;this.verified=false;return true;}
  canSubmit(){return this.isCurrent(this.token)&&this.verified&&this.revision!==null;}
  submission(){if(!this.canSubmit())throw Error('当前复核尚未完成读取校验');return Object.freeze({id:this.token.id,expected_revision:this.revision});}
  close(){if(this.controller)this.controller.abort();this.controller=null;this.token=null;this.verified=false;this.revision=null;this.epoch++;}
}
if(typeof module!=='undefined'&&module.exports)module.exports=ReviewSession;
