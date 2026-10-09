"""Metadata helper for the manually invoked reviewed cleanup. Never removes files."""
from pathlib import Path
import json, sqlite3, sys

root=Path(__file__).resolve().parents[1]
plan=json.loads((root/'reports/storage_20260926/cleanup_plan.json').read_text(encoding='utf-8-sig'))
phase=sys.argv[1]
if phase not in ('audit','prepare'):raise ValueError('Unknown phase')
dbpath=root/'review_records/inspection.sqlite3'
con=sqlite3.connect(f'{dbpath.as_uri()}?mode=rw',uri=True)
ids=plan['archive_ids_to_remove']
assert len(ids)==3448 and not set(ids).intersection(plan['keep_ids'])
remaining=[]
for key in ids:
    row=con.execute('SELECT status,note FROM events WHERE id=?',(key,)).fetchone()
    if row:
        if row[0]!='pending' or row[1] not in (None,''):
            raise RuntimeError(f'{key} has a review/note; preserve it and review the plan again')
        remaining.append(key)
print(f'Metadata audit: {len(remaining)} unreviewed rows selected; other rows remain unchanged')
if phase=='prepare':
    backup=root/'reports/storage_20260926/cleanup_metadata_backup.sqlite3'
    if not backup.exists():
        dest=sqlite3.connect(backup);con.backup(dest);dest.close()
    with con:
        con.executemany("DELETE FROM events WHERE id=? AND status='pending' AND COALESCE(note,'')=''",[(key,) for key in remaining])
    con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    con.execute('VACUUM')
    print('Selected metadata removed; backup contains metadata only, not images')
con.close()
