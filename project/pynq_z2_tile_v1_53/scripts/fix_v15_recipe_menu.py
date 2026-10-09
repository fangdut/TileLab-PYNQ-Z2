from pathlib import Path
p=Path(__file__).resolve().parents[1]/'host/workstation.html'
s=p.read_text(encoding='utf-8')
old="function render(){const s=state,rs=s.records||[];"
new="""function render(){const s=state,rs=s.records||[];
const menu=$('recipe'),menuData=JSON.stringify((s.recipes||[]).map(r=>[r.id,r.name]));
if(menu.dataset.catalog!==menuData){
 const options=(s.recipes||[]).map(r=>{const o=document.createElement('option');o.value=r.id;o.textContent=r.name;return o});
 const custom=document.createElement('option');custom.value='custom';custom.textContent='自定义参数';
 menu.replaceChildren(...options,custom);menu.dataset.catalog=menuData;menu.value=s.requested_recipe;
}
"""
assert old in s
s=s.replace(old,new,1)
s=s.replace('</style>','.events>.panel-head{flex-wrap:wrap}.event-tools{flex-wrap:wrap}.event-tools select{width:auto;min-width:132px}\n</style>',1)
p.write_text(s,encoding='utf-8')
