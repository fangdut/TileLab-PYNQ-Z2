from pathlib import Path
import argparse,hashlib,json,zipfile
def verify(root,manifest):
    root=Path(root).resolve();m=json.loads(Path(manifest).read_text(encoding='utf8'));files=m['files']
    if not isinstance(files,dict) or not files:raise ValueError('Empty or invalid file manifest')
    for name,digest in files.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('File missing or changed: '+name)
    xsa=root/'system.xsa';bit=root/'system.bit'
    if xsa.exists() or bit.exists():
        if not xsa.exists() or not bit.exists():raise ValueError('Expected matching XSA and BIT')
        with zipfile.ZipFile(xsa) as z:
            names=[n for n in z.namelist() if n.endswith('.bit')]
            if len(names)!=1 or hashlib.sha256(z.read(names[0])).digest()!=hashlib.sha256(bit.read_bytes()).digest():raise ValueError('XSA/BIT mismatch')
    return dict(integrity_verified=True,files=len(files),actual_hardware_verified=False)
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--manifest',required=True,type=Path);a=p.parse_args();print(json.dumps(verify(a.root,a.manifest)))
if __name__=='__main__':main()
