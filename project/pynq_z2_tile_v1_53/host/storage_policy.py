"""Bounded evidence storage. No background deletion or image classification."""
import json
from pathlib import Path

class ArchiveCapacityError(OSError):
    pass

class StoragePolicy:
    def __init__(self, root):
        self.path=Path(root)/'host/storage_policy.json'
        self.mode='preview';self.max_archive_mib=1024
        if self.path.exists():
            data=json.loads(self.path.read_text(encoding='utf-8-sig'))
            self.validate(data.get('mode'),data.get('max_archive_mib'))
            self.mode=data['mode'];self.max_archive_mib=data['max_archive_mib']
    @staticmethod
    def validate(mode, limit):
        if mode not in ('preview','archive'):raise ValueError('Unknown storage mode')
        if type(limit) is not int or not 16<=limit<=102400:raise ValueError('存档上限须为 16 至 102400 MiB')
    def write(self, mode, limit, atomic):
        self.validate(mode,limit)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        atomic(self.path,json.dumps(dict(mode=mode,max_archive_mib=limit),indent=2).encode())
        self.mode=mode;self.max_archive_mib=limit
    @property
    def max_bytes(self):return self.max_archive_mib*1024*1024
