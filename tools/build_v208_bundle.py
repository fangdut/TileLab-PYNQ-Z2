"""Reconstruct the exact V208 delivery from versioned sources, without hardware."""
from pathlib import Path
import argparse,hashlib,json,shutil

def build(repo,output):
    repo=Path(repo).resolve();output=Path(output).resolve()
    if output.exists() and any(output.iterdir()):raise ValueError('Output directory must be empty')
    rows=json.loads((repo/'release/v208/bundle_sources.json').read_text(encoding='utf8'))['files']
    for row in rows:
        src=(repo/row['source']).resolve();dst=(output/row['path']).resolve()
        if not src.is_relative_to(repo) or not dst.is_relative_to(output):raise ValueError('Unsafe map path')
        if src.stat().st_size!=row['bytes'] or hashlib.sha256(src.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Source mismatch: '+row['source'])
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    print(json.dumps({'files':len(rows),'output':str(output),'board_operation':False}))
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    build(Path(__file__).resolve().parents[1],a.out)
