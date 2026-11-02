"""Generic SHA256 bundle verification; standard library, no board dependency."""
from pathlib import Path
import argparse
import hashlib
import json


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf8'))
    files = manifest['files']
    if not files:
        raise ValueError('Empty manifest')
    for name, record in files.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe manifest path: '+name)
        file = (root/relative).resolve()
        if not file.is_relative_to(root):
            raise ValueError('Path escapes root: '+name)
        if not file.is_file() or file.stat().st_size != record['bytes']:
            raise ValueError('Missing or wrong size: '+name)
        digest = hashlib.sha256()
        with file.open('rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                digest.update(block)
        if digest.hexdigest() != record['sha256']:
            raise ValueError('Hash mismatch: '+name)
    return dict(verified_files=len(files),scope='INTEGRITY_AGAINST_LOCAL_MANIFEST_NOT_AUTHENTICITY')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('root', type=Path)
    print(json.dumps(verify(p.parse_args().root)))
