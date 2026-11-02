"""Restore byte-exact engineering filenames from the normalized submission."""
from pathlib import Path
import argparse,hashlib,json,shutil

def restore(package,output=None,verify_only=False):
    package=Path(package).resolve()
    rows=json.loads((package/'build/file_map.json').read_text(encoding='utf8'))['files']
    target=Path(output).resolve() if output is not None else None
    if not verify_only:
        if target is None:raise ValueError('--out is required unless --verify-only')
        if target==package or target.is_relative_to(package):raise ValueError('Restore outside the submitted source directory')
        if target.exists() and any(target.iterdir()):raise ValueError('Output directory must be empty')
    for row in rows:
        src=(package/row['source']).resolve()
        if not src.is_relative_to(package):raise ValueError('Source escapes package')
        raw=src.read_bytes()
        if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('Source hash or size mismatch: '+row['source'])
        rel=Path(row['original'])
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe destination')
        if not verify_only:
            dst=(target/rel).resolve()
            if not dst.is_relative_to(target):raise ValueError('Destination escapes output')
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    result=dict(verified_engineering_files=len(rows),restored=not verify_only,board_operation=False)
    print(json.dumps(result));return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    restore(Path(__file__).resolve().parents[1],a.out,a.verify_only)
