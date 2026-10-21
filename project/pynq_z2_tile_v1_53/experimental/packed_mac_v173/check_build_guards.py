"""Reject incompatible packed weights and unsafe signed24 accumulators."""
from pathlib import Path
import argparse,importlib.util,json,struct,tempfile


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--profile',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('candidate',root/'scripts/texture_v170/build_candidate.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    graph=json.loads((a.profile/'graph.json').read_text())
    source=Path(__file__).with_name('texture_packed_narrow.cpp')
    valid=module.packed_weight_proof(source,a.profile,graph)
    if not valid:raise ValueError('Packed source marker missing')
    original=(a.profile/'model.bin').read_bytes();task=next(t for t in graph['tasks'] if t[0] in (1,2))
    with tempfile.TemporaryDirectory(prefix='tilelab_guard_') as directory:
        folder=Path(directory);blob=bytearray(original);blob[task[4]*8]=128
        (folder/'model.bin').write_bytes(blob)
        try:module.packed_weight_proof(source,folder,graph)
        except ValueError as error:weight_rejected=str(error)=='Centered packing rejects -128 weights'
        else:weight_rejected=False
        multipliers=struct.unpack_from('<'+str(task[10])+'I',original,task[6]*4)
        channel=next(i for i,v in enumerate(multipliers) if v)
        blob=bytearray(original);struct.pack_into('<i',blob,(task[5]+channel)*4,1<<23)
        (folder/'model.bin').write_bytes(blob)
        try:module.packed_weight_proof(source,folder,graph)
        except ValueError as error:accumulator_rejected=str(error)=='Active convolution accumulator exceeds signed24 range'
        else:accumulator_rejected=False
    if not weight_rejected or not accumulator_rejected:raise ValueError('Unsafe model accepted')
    report=dict(scope='BUILD_GUARD_POSITIVE_AND_INCOMPATIBLE_MODEL_NEGATIVE_CHECKS',valid_model=valid,
        minus128_model_rejected=weight_rejected,excessive_accumulator_rejected=accumulator_rejected)
    a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
