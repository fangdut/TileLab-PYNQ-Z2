"""Export a canonical migration program; NOT compatible with legacy firmware."""
from pathlib import Path
import argparse,json,hashlib,sys,torch,contextlib,io,operator
import numpy as np
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--integer',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
    sys.path.insert(0,str(a.source));from hfenet import HFENet
    with contextlib.redirect_stdout(io.StringIO()):net=HFENet()
    net.load_state_dict(torch.load(a.source/'checkpoint/model_epoch_69.pth',map_location='cpu',weights_only=True)['model']);net.eval();g=torch.fx.symbolic_trace(net)
    cal=json.loads((a.integer/'calibration_frozen.json').read_text());traces={r['node']:r for r in json.loads((a.integer/'integer_trace.json').read_text())};exponents=json.loads((a.integer/'weight_exponents.json').read_text());weights=np.load(a.integer/'integer_weights.npz',allow_pickle=False)
    tensors={};ops=[];payload=bytearray();tensor_id=0
    for node in g.graph.nodes:
        if node.op=='output':output=tensors[node.args[0].name]['id'];continue
        info=dict(id=tensor_id,name=node.name,shape=cal['shapes'][node.name],exponent=0 if node.op=='placeholder' else traces[node.name]['exp'],dtype='int16' if node.target!='sigmoid' else 'uint8');tensor_id+=1;tensors[node.name]=info
        if node.op=='placeholder':input_id=info['id'];continue
        inputs=[tensors[n.name]['id'] for n in node.all_input_nodes];op=dict(name=node.name,input_tensors=inputs,output_tensor=info['id'])
        if node.op=='call_module':
            m=g.get_submodule(node.target)
            if isinstance(m,torch.nn.Conv2d):
                q=weights[node.name].astype('<i2');padding=(-len(payload))%64;payload.extend(b'\0'*padding);offset=len(payload);raw=q.tobytes(order='C');payload.extend(raw)
                op.update(kind='conv2d_int16_mac48',weights_offset=offset,weights_bytes=len(raw),weights_sha256=hashlib.sha256(raw).hexdigest(),weights_shape=list(q.shape),weight_exponents=exponents[node.name],stride=list(m.stride),padding=list(m.padding),dilation=list(m.dilation),groups=m.groups,requant='signed_nearest_even_saturate16')
            elif isinstance(m,torch.nn.InstanceNorm2d):
                source=tensors[node.args[0].name];sx=source['exponent'];n=info['shape'][-1]*info['shape'][-2]
                op.update(kind='dynamic_integer_instance_norm',pixels_per_channel=n,gamma_q30=[int(round(float(v.detach())*2**30)) for v in m.weight],beta_q30=[int(round(float(v.detach())*2**30)) for v in m.bias],epsilon_integer=[str(int(round(m.eps*n*n*2.0**(-2*(sx[c] if isinstance(sx,list) else sx))))) for c in range(info['shape'][1])],coefficient_fraction_bits=36,sqrt='floor_integer_sqrt128',rounding='nearest_even')
            elif isinstance(m,torch.nn.ReLU):op.update(kind='relu_requant16')
            elif isinstance(m,torch.nn.MaxPool2d):op.update(kind='max_pool_2x2_stride2')
            elif isinstance(m,torch.nn.Upsample):op.update(kind='bilinear_2x_quarter_weights',align_corners=False,edge='replicate',combined_denominator=16)
            elif isinstance(m,torch.nn.Sigmoid):op.update(kind='logit_greater_than_zero')
            else:raise ValueError(type(m))
        elif node.target is operator.add:op.update(kind='residual_add_requant16')
        elif node.target is torch.cat:op.update(kind='channel_concat_requant16')
        else:raise ValueError(node)
        ops.append(op)
    (a.out/'weights_int16.bin').write_bytes(payload)
    program=dict(format='TILELAB_197_MIGRATION_PREVIEW_NOT_LEGACY_ABI',geometry=[256,1408],input='author3integerchannels_after_PL_histogram_preprocessor',tensors=list(tensors.values()),operators=ops,input_tensor=input_id,output_tensor=output,weight_payload_sha256=hashlib.sha256(payload).hexdigest(),legacy_firmware_compatible=False,full_hardware_implemented=False,training=False)
    (a.out/'operator_program.json').write_text(json.dumps(program,indent=2),encoding='utf8')
    proof=dict(scope='CANONICAL_INTEGER_PROGRAM_EXPORT_NOT_BOARD_EXECUTABLE',operators=len(ops),tensors=len(tensors),conv_operators=sum(o['kind']=='conv2d_int16_mac48' for o in ops),norm_operators=sum(o['kind']=='dynamic_integer_instance_norm' for o in ops),weight_payload_bytes=len(payload),weight_payload_sha256=program['weight_payload_sha256'],program_sha256=hashlib.sha256((a.out/'operator_program.json').read_bytes()).hexdigest(),legacy_firmware_compatible=False,full_hardware_implemented=False,model_payload_kept_local=True)
    (a.out/'proof.json').write_text(json.dumps(proof,indent=2),encoding='utf8');print(json.dumps(proof))
if __name__=='__main__':main()
