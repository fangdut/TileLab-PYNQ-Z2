"""Design-time threshold update from verified FPGA normal calibration only."""
from pathlib import Path
import argparse,hashlib,json,shutil,struct,zlib
import numpy as np
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    rows=json.loads((a.dataset/'manifest.json').read_text())['images'];records=json.loads((a.calibration/'results.json').read_text());expected={r['id'] for r in rows if r['role']=='calibration'}
    assert len(records)==32 and {r['id'] for r in records}==expected
    graph=json.loads((a.base/'graph.json').read_text());old=(a.base/'model.bin').read_bytes();assert sha(a.base/'model.bin')==graph['sha256']
    assert all(r['label']=='good' and r['role']=='calibration' and r['result']['model_sha256']==graph['sha256'] and not r['result']['cpu_detection'] and not r['result']['gpu_detection'] for r in records)
    threshold=max(graph['threshold'],max(int(r['result']['pl_peak']) for r in records)+1)
    new=bytearray(old);struct.pack_into('<I',new,60,threshold);assert old[:60]==new[:60] and old[64:]==new[64:]
    a.out.mkdir(parents=True,exist_ok=False)
    for name in ['quantized_graph.pt','integer_head.npz']:
        if (a.base/name).is_file():shutil.copy2(a.base/name,a.out/name)
    if (a.out/'integer_head.npz').is_file():
        head=dict(np.load(a.out/'integer_head.npz'));head['threshold']=np.array(threshold);np.savez_compressed(a.out/'integer_head.npz',**head)
    (a.out/'model.bin').write_bytes(new)
    graph.update(threshold=threshold,sha256=sha(a.out/'model.bin'),crc32=zlib.crc32(new));(a.out/'graph.json').write_text(json.dumps(graph,indent=2))
    proof=dict(scope='OFFLINE_NORMAL_ONLY_THRESHOLD_EXTENSION_FPGA_SCORING',base_model_sha256=sha(a.base/'model.bin'),candidate_model_sha256=graph['sha256'],old_threshold=struct.unpack_from('<I',old,60)[0],new_threshold=threshold,only_changed_binary_range=[60,64],unchanged_cnn_projection_and_reference_centers=True,calibration_count=32,calibration_results_sha256=sha(a.calibration/'results.json'),manifest_sha256=sha(a.dataset/'manifest.json'),reserved_final_scored=False,physical_specimen_independence=False)
    (a.out/'calibration_frozen.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof))
if __name__=='__main__':main()
