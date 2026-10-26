from pathlib import Path
import json,sys,torch,contextlib,io,math
W=Path('D:/Vivado/TileLab_RealPhotos_20261020');S=W/'v197_hfenet_source01';sys.path.insert(0,str(S));from hfenet import HFENet
with contextlib.redirect_stdout(io.StringIO()):net=HFENet()
net.load_state_dict(torch.load(S/'checkpoint/model_epoch_69.pth',map_location='cpu',weights_only=True)['model']);net.eval();graph=torch.fx.symbolic_trace(net)
cal=json.loads((W/'v197_integer01/calibration_frozen.json').read_text());nodes=list(graph.graph.nodes);last={node.name:max([nodes.index(u) for u in node.users] or [len(nodes)]) for node in nodes};live={};peak=0;history=[]
for i,node in enumerate(nodes):
    if node.name in cal['shapes'] and node.op!='output':
        bytes=math.prod(cal['shapes'][node.name])*(1 if node.target=='sigmoid' else 2);live[node.name]=bytes;peak=max(peak,sum(live.values()))
        history.append(dict(node=node.name,bytes=bytes,live_bytes=sum(live.values()),live_tensors=list(live)))
    for name in list(live):
        if last[name]<=i:del live[name]
actual=json.loads((W/'v197_author01/executed_graph.json').read_text());qops=sum(v.size for v in __import__('numpy').load(W/'v197_integer01/integer_weights.npz').values())
result=dict(scope='LOGICAL_TENSOR_LIVENESS_AND_MAC_LOWER_BOUND_NOT_IMPLEMENTED_RESOURCE_OR_FPS',geometry=[256,1408],peak_simultaneous_int16_tensor_bytes=peak,weight_int16_bytes=qops*2,declared_parameters=actual['declared_parameters'],executed_conv_weights=qops,macs=actual['macs_original'],assumptions=['Separate output tensor allocated before freeing final-use inputs; conservative logical liveness','No claim of contiguous-memory allocator feasibility, burst bandwidth or clock closure','Additional padding, accumulators, histogram and transport buffers must be reserved','16x16 integer DSP MAC, all cycles utilized only in theoretical bounds'],ideal_mac_seconds_at_100mhz={str(n):actual['macs_original']/(n*100_000_000) for n in [32,64,128]},history=history)
(W/'v197_integer01/memory_and_ops_plan.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k!='history'}))
