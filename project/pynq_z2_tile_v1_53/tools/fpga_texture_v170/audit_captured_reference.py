"""OFFLINE audit of a saved input/result; never part of the video runtime.

HDMI scaling changes pixels. Compare the actual captured RGB, rather than
reusing expected scores for a different-size original photograph.
"""
from pathlib import Path
import argparse,json
import numpy as np
import torch
from prepare_integer import FixedGraph,project,integer_scores
from export_integer import export
from evaluate_lightweight import sha,save
from validate_full_c import mask_reference


def main():
    p=argparse.ArgumentParser()
    for n in ['profile','image','result','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(4)
    metadata=json.loads((a.profile/'graph.json').read_text())
    if sha(a.profile/'model.bin')!=metadata['sha256']:raise ValueError('Frozen model changed')
    saved=torch.load(a.profile/'quantized_graph.pt',weights_only=True,map_location='cpu')
    head=np.load(a.profile/'integer_head.npz',allow_pickle=False)
    rebuilt=a.out/'reference_model';rebuilt.mkdir()
    rebuilt_metadata=export(rebuilt,saved,head,saved['side'])
    if rebuilt_metadata['sha256']!=metadata['sha256']:
        raise ValueError('Python graph/head do not reproduce the deployed model bytes')
    g=FixedGraph.__new__(FixedGraph)
    for k,v in saved.items():setattr(g,k,v)
    g.feature_dim=128;g.fixed_input=True
    g.input_m=head['input_m'].tolist();g.input_b=head['input_b'].tolist()
    codes=g.forward(a.image,integer=True,output_codes=True)
    q=project(codes,torch.from_numpy(head['projection'].astype('i4')),
              torch.from_numpy(head['bias'].astype('i8')),int(head['shift']))
    scores=integer_scores(q,torch.from_numpy(head['centers'].astype('i4')),metadata['grid']).numpy()
    from PIL import Image
    with Image.open(a.image) as im:w,h=im.size
    raw=np.fromfile(a.result,dtype='<u4');grid=metadata['grid'];threshold=metadata['threshold']
    if len(raw)!=16+grid*grid+w*h or raw[0]!=0x17000001 or raw[1] or raw[5]!=grid or raw[7]!=w*h or raw[8]!=metadata['steps']:
        raise ValueError('Saved result header/length invalid')
    actual=raw[16:16+grid*grid].reshape(grid,grid)
    mask=raw[16+grid*grid:].reshape(h,w)
    expected_mask=mask_reference(scores,w,h,threshold)
    error=int(np.abs(actual.astype('i8')-scores).max())
    mismatch=int(np.count_nonzero(mask!=expected_mask))
    header_ok=(int(raw[2])==int(scores.max()>threshold) and int(raw[3])==int(scores.max())
               and int(raw[4])==threshold and int(raw[6])==int(expected_mask.sum()))
    np.save(a.out/'independent_reference_scores.npy',scores,allow_pickle=False)
    report=dict(scope='OFFLINE_SAVED_INPUT_REFERENCE_AUDIT_NOT_A_NEW_BOARD_RUN',
        cpu_used_only_for_offline_audit=True,model_rebuilt_byte_exact=True,
        model_sha256=metadata['sha256'],image_sha256=sha(a.image),saved_result_sha256=sha(a.result),
        quantized_graph_sha256=sha(a.profile/'quantized_graph.pt'),head_sha256=sha(a.profile/'integer_head.npz'),
        grid_max_error=error,mask_mismatches=mismatch,result_header_exact=header_ok,
        all_values_exact=not error and not mismatch and header_ok,
        accuracy_scope='Numerical equivalence only; no ground-truth claim')
    save(a.out/'audit.json',report);print(json.dumps(report),flush=True)
    if not report['all_values_exact']:raise RuntimeError('Saved result differs from the independent frozen Python reference')


if __name__=='__main__':main()
