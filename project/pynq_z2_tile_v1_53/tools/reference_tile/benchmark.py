"""Predeclared mechanism audit. Synthetic defects are NEVER real accuracy evidence."""
from pathlib import Path
import argparse,base64,hashlib,io,json,time
import numpy as np
from PIL import Image
from reference_tile import ROOT,compare,policy,components,integer_difference,save_result,sha,canonical
from fixtures import STYLES,frame,capture,add_defect

def make_cases():
    cases=[]
    normals=[('identity',{}),('integer_shift',dict(dx=2,dy=-1,noise=1)),('fractional_shift',dict(dx=.375,dy=-.25,noise=1)),('color_cast',dict(dx=-1,dy=2,gains=(1.04,.97,1.02),offsets=(2,-3,1),noise=1)),('mild_blur',dict(blur=.25,noise=.5)),('jpeg92',dict(jpeg=92))]
    for i,style in enumerate(STYLES):
        reference=frame(style)
        for name,kwargs in normals:cases.append(dict(id=f'{style}_normal_{name}',cohort='PROCEDURAL_NORMAL_CAPTURE_SIMULATION',style=style,reference=reference,current=capture(reference,**kwargs),truth=np.zeros((500,500),bool),expected='no_candidate',parameters=kwargs))
        for width,bright,edge in [(1,False,False),(2,False,False),(1,True,False),(3,False,True)]:
            current,truth=add_defect(reference,width,bright,edge)
            kwargs=dict(dx=1,dy=-1,gains=(.98,1.01,.99),noise=.5)
            cases.append(dict(id=f'{style}_line_w{width}_bright{int(bright)}_edge{int(edge)}',cohort='PROCEDURAL_ARTIFICIAL_LINE',style=style,reference=reference,current=capture(current,**kwargs),truth=truth,expected='localized_candidate',parameters=dict(width=width,bright=bright,edge=edge,capture=kwargs)))
        invalid=[('wrong_pattern',frame(STYLES[(i+1)%len(STYLES)])),('shift6',capture(reference,dx=6)),('rotation',capture(reference,angle=.8)),('dark_exposure',capture(reference,gains=(.55,.55,.55)))]
        blocked=reference.copy();blocked[170:520,470:720]=240;invalid.append(('occluded',blocked))
        for name,current in invalid:cases.append(dict(id=f'{style}_invalid_{name}',cohort='PROCEDURAL_REJECT_OR_REVIEW_STRESS',style=style,reference=reference,current=current,truth=np.zeros((500,500),bool),expected='not_clean',parameters=dict(condition=name)))
    # These are existing unmodified good photos. Exact self comparisons test
    # plumbing only. They are NOT independent normal samples or crack evidence.
    rows=json.loads((ROOT/'data/real_tiles/hdmi_manifest.json').read_text())['items']
    for r in rows:
        if r['label']!='good':continue
        path=ROOT/'data/real_tiles'/r['image']
        with Image.open(path) as im:a=np.array(im.convert('RGB'))
        cases.append(dict(id=f"mvtec_{r['index']:03}_identity",cohort='REAL_GOOD_PHOTO_IDENTITY_DIAGNOSTIC_NOT_ACCURACY',style='mvtec',reference=a,current=a,truth=np.zeros((500,500),bool),expected='no_candidate',parameters=dict(image=r['image'],source_sha256=sha(path))))
    return cases

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False);p=policy();cases=make_cases();start=time.perf_counter()
    declaration=dict(scope='PREDECLARED ENGINEERING MECHANISM TEST ONLY; not painted-tile real accuracy, no physical good/crack pairs, no board test',policy=p,policy_sha256=hashlib.sha256(canonical(p)).hexdigest(),source_sha256={name:sha(Path(__file__).with_name(name)) for name in ['reference_tile.py','fixtures.py','benchmark.py']},cases=[{k:v for k,v in c.items() if k not in ('reference','current','truth')} for c in cases],real_positive_pairs=0)
    (a.out/'declaration.json').write_text(json.dumps(declaration,indent=2)+'\n');rows=[]
    for index,c in enumerate(cases):
        result,mask,aligned=compare(c['reference'],c['current'],p);truth=c['truth'];tp=int((mask&truth).sum()) if mask is not None else 0;fp=int((mask&~truth).sum()) if mask is not None else 0
        ref=c['reference'][110:610,390:890];current=c['current'][110:610,390:890]
        _,_,strong,weak=integer_difference(ref,current,[256]*3,[0]*3,np.zeros((500,500),np.uint8),p['high'],p['low']);_,naive=components(weak,strong,p)
        success=(result['status']=='COMPARED' and not result['alarm']) if c['expected']=='no_candidate' else (bool(result['alarm']) and tp>0) if c['expected']=='localized_candidate' else not(result['status']=='COMPARED' and result['alarm'] is False)
        row=dict(id=c['id'],cohort=c['cohort'],style=c['style'],expected=c['expected'],mechanism_expectation_met=bool(success),truth_pixels=int(truth.sum()),tp=tp,fp=fp,pixel_recall=tp/int(truth.sum()) if truth.any() else None,naive_difference_alarm=bool(naive),**result);rows.append(row)
        out=a.out/c['id'];save_result(out,row,mask,aligned);Image.fromarray(c['reference']).save(out/'reference.png');Image.fromarray(c['current']).save(out/'current.png');Image.fromarray(truth.astype(np.uint8)*255).save(out/'truth.png')
        print(json.dumps(dict(index=index+1,id=c['id'],status=result['status'],alarm=result['alarm'],met=bool(success),reason=result.get('reason'),recall=row['pixel_recall'])),flush=True)
    summaries={}
    for name in sorted({r['cohort'] for r in rows}):
        selected=[r for r in rows if r['cohort']==name];summaries[name]=dict(cases=len(selected),compared=sum(r['status']=='COMPARED' for r in selected),rejected=sum(r['status']=='REJECTED_INPUT' for r in selected),alarms=sum(r['alarm'] is True for r in selected),no_candidate=sum(r['alarm'] is False for r in selected),expectations_met=sum(r['mechanism_expectation_met'] for r in selected),naive_alarms=sum(r['naive_difference_alarm'] for r in selected))
    report=dict(scope=declaration['scope'],accuracy_qualified=False,real_positive_pairs=0,independent_real_material_validation_count=0,board_integrated=False,policy_sha256=declaration['policy_sha256'],cohorts=summaries,seconds=time.perf_counter()-start,failed_cases=[r['id'] for r in rows if not r['mechanism_expectation_met']],rows=rows)
    (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)

if __name__=='__main__':main()
