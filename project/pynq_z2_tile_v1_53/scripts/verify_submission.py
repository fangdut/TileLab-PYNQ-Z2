"""Verify frozen code, input, PDFs, evidence and accepted artifacts; read only."""
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parents[1]
def main():
    manifest=json.loads((R/'DELIVERY_MANIFEST.json').read_text(encoding='utf-8'))
    errors=[]
    for name,digest in manifest['frozen_sha256'].items():
        path=R/name
        if not path.is_file():errors.append('missing '+name)
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=digest:errors.append('changed '+name)
    print(json.dumps(dict(verified=not errors,files=len(manifest['frozen_sha256']),errors=errors),ensure_ascii=False))
    return int(bool(errors))
if __name__=='__main__':sys.exit(main())
