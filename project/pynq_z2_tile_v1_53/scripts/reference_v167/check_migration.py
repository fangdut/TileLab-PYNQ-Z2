"""Migration equivalence on procedural fixtures; not board or accuracy evidence."""
from pathlib import Path
import argparse,sys,json,hashlib,time
import numpy as np
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/reference_tile'))
import fixtures,reference_v166 as old,frame_v167 as new
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);rows=[]
    for style in fixtures.STYLES:
        ref=fixtures.frame(style);defect,_=fixtures.add_defect(ref,width=1)
        for name,cur in [('good',fixtures.capture(ref,dx=.75,dy=-.5,noise=.7)),('line',fixtures.capture(defect,dx=.75,dy=-.5,noise=.7)),('invalid_pose',fixtures.capture(ref,dx=6))]:
            expected,mask,_=old.compare(ref,cur);prepared,pair,aligned,_=new.prepare(ref,cur)
            if pair is None:
                actual=prepared;got=None
            else:
                words=new.oracle(pair,prepared['photometric'])
                # Explicit test double, never counted as board proof.
                proof=dict(output_crc_verified=True,paired_sha256=prepared['paired_sha256'],pl_id=0x16700601,firmware=0x16700,test_double=True)
                actual,got=new.finish(prepared,words,proof)
            same=(expected['status'],expected['alarm'],expected.get('reason'))==(actual['status'],actual['alarm'],actual.get('reason')) and ((got is None and mask is None) or (got is not None and mask is not None and np.array_equal(got,mask)))
            row=dict(style=style,case=name,equivalent=bool(same),status=actual['status'],alarm=actual['alarm']);rows.append(row);print(json.dumps(row),flush=True)
            if not same:raise RuntimeError('V166 migration differs: '+str(row))
    result=dict(scope='PROCEDURAL_MIGRATION_EQUIVALENCE_WITH_SOFTWARE_SCORE_TEST_DOUBLE_NOT_BOARD_NOT_ACCURACY',passed=True,rows=rows,source_sha256={str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(new.__file__),Path(old.__file__),Path(__file__)]})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
