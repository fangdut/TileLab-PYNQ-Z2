"""Reject model descriptors that invalidate the specialized address generator."""
from pathlib import Path
import argparse,copy,hashlib,json,struct,sys,zlib
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'tools/fpga_texture_v170'))
from check_spatial_coordinates import inspect
def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    source=Path(__file__).with_name('texture_spatial_lut.cpp');proof=inspect(source,a.profile);assert proof['passed']
    a.out.mkdir(parents=True,exist_ok=False);graph=json.loads((a.profile/'graph.json').read_text());blob=bytearray((a.profile/'model.bin').read_bytes())
    index=next(i for i,t in enumerate(graph['tasks']) if t[0]==1 and t[11]==3)
    changed=copy.deepcopy(graph);changed['tasks'][index][9]=16
    struct.pack_into('<I',blob,(64+index*24+9)*4,16)
    changed['sha256']=hashlib.sha256(blob).hexdigest();changed['crc32']=zlib.crc32(blob)
    (a.out/'model.bin').write_bytes(blob);(a.out/'graph.json').write_text(json.dumps(changed))
    try:inspect(source,a.out)
    except ValueError as e:
        assert 'input channels above8' in str(e)
    else:raise AssertionError('Unsupported standard3x3 accepted')
    # Keep the bad descriptor graph but restore the original bytes: provenance
    # is checked independently of the arithmetic-domain restriction.
    (a.out/'model.bin').write_bytes((a.profile/'model.bin').read_bytes())
    try:inspect(source,a.out)
    except ValueError as e:assert 'provenance mismatch' in str(e)
    else:raise AssertionError('Mismatched graph/model accepted')
    j=dict(scope='MODEL_BINDING_NEGATIVE_TESTS_NOT_RTL_OR_BOARD',passed=True,
           actual_model_accepted=True,synthetic_ic16_descriptor_rejected=True,mismatched_model_graph_rejected=True,
           source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),model_sha256=proof['model_sha256'])
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
if __name__=='__main__':main()
