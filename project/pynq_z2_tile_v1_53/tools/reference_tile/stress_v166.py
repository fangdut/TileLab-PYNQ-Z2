"""Declared procedural stress; NEVER independent real accuracy evidence."""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from PIL import Image
from fixtures import STYLES,frame,capture,add_defect
import reference_tile as base
import reference_v166 as candidate

def cases():
    normals=[dict(jpeg=95),dict(jpeg=90),dict(dx=.1875,dy=-.4375,noise=.75,jpeg=95),dict(dx=-2,dy=1,gains=(.98,1.03,1.01),noise=.5,jpeg=95),dict(blur=.35,noise=1),dict(dx=-.625,dy=.3125,gains=(1.03,.98,1.01),noise=.5)]
    for style in STYLES:
        ref=frame(style)
        for i,params in enumerate(normals):yield dict(id=f'{style}_normal_{i}',group='NORMAL_COMBINED_PERTURBATIONS',reference=ref,current=capture(ref,seed=166+i,**params),truth=np.zeros((500,500),bool),parameters=params)
        for i,(contrast,width,bright,edge,params) in enumerate([
            (75,1,False,False,dict(jpeg=92)),(75,1,True,False,dict(jpeg=90)),
            (75,2,False,True,dict(dx=.1875,dy=-.4375,jpeg=95,noise=.5)),
            (35,1,False,False,dict()),(35,1,False,False,dict(jpeg=92)),
            (20,1,False,False,dict(jpeg=95)),
        ]):
            _,truth=add_defect(ref,width,bright,edge);cur=ref.copy();tile=cur[110:610,390:890].astype(np.int16)
            tile[truth]=np.clip(tile[truth]+(contrast if bright else -contrast),0,255);cur[110:610,390:890]=tile.astype(np.uint8)
            yield dict(id=f'{style}_line_{i}',group='ARTIFICIAL_LUMA_LINES',reference=ref,current=capture(cur,seed=166+i,**params),truth=truth,parameters=dict(contrast=contrast,width=width,bright=bright,edge=edge,capture=params))
        # Exactly isoluminant delta in the integer Y=(R+2G+B+2)>>2 metric.
        for width in (1,3):
            _,truth=add_defect(ref,width);cur=ref.copy();tile=cur[110:610,390:890].astype(np.int16)
            tile[truth]=np.clip(tile[truth]+np.array([40,0,-40]),0,255);cur[110:610,390:890]=tile.astype(np.uint8)
            yield dict(id=f'{style}_color_line_w{width}',group='ISOLUMINANT_COLOR_CHANGE_LIMIT',reference=ref,current=cur,truth=truth,parameters=dict(delta=[40,0,-40],width=width))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    p=candidate.policy();allcases=list(cases())
    declaration=dict(scope='SYNTHETIC_PROCEDURAL_STRESS_NOT_REAL_ACCURACY_NOT_BOARD',accuracy_qualified=False,policy=p,implementation=candidate.implementation(),source_sha256=base.sha(__file__),fixtures_sha256=base.sha(Path(__file__).with_name('fixtures.py')),cases=[{k:v for k,v in c.items() if k not in ('reference','current','truth')} for c in allcases])
    (args.out/'declaration.json').write_text(json.dumps(declaration,indent=2)+'\n',encoding='utf8');rows=[]
    for index,c in enumerate(allcases):
        r,m,aligned=candidate.compare(c['reference'],c['current']);truth=c['truth'];tp=int((m&truth).sum()) if m is not None else 0;fp=int((m&~truth).sum()) if m is not None else 0
        success=r['status']=='COMPARED' and ((not r['alarm']) if not truth.any() else (r['alarm'] and tp>0))
        row=dict(id=c['id'],group=c['group'],parameters=c['parameters'],truth_pixels=int(truth.sum()),tp=tp,fp=fp,pixel_recall=tp/int(truth.sum()) if truth.any() else None,expectation_met=bool(success),reference_array_sha256=hashlib.sha256(c['reference'].tobytes()).hexdigest(),current_array_sha256=hashlib.sha256(c['current'].tobytes()).hexdigest(),**r);rows.append(row)
        if not success or c['id'] in ('floral_normal_0','floral_line_0','floral_line_2','floral_color_line_w1'):
            out=args.out/c['id'];base.save_result(out,row,m,aligned)
            for key in ('reference','current'):Image.fromarray(c[key]).save(out/(key+'.png'))
            Image.fromarray(truth.astype(np.uint8)*255).save(out/'truth.png')
        print(json.dumps(dict(index=index+1,id=c['id'],status=r['status'],alarm=r['alarm'],recall=row['pixel_recall'],met=bool(success),reason=r.get('reason'))),flush=True)
    groups={}
    for name in sorted({r['group'] for r in rows}):
        s=[r for r in rows if r['group']==name];groups[name]=dict(cases=len(s),compared=sum(r['status']=='COMPARED' for r in s),rejected=sum(r['alarm'] is None for r in s),alarms=sum(r['alarm'] is True for r in s),no_candidate=sum(r['alarm'] is False for r in s),localized=sum(r['tp']>0 for r in s),minimum_pixel_recall=min((r['pixel_recall'] for r in s if r['pixel_recall'] is not None),default=None))
    result=dict(scope=declaration['scope'],accuracy_qualified=False,implementation=candidate.implementation(),groups=groups,failures=[r['id'] for r in rows if not r['expectation_met']],rows=rows)
    (args.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)

if __name__=='__main__':main()
