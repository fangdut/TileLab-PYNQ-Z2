"""Bounded capacity/CLI experiment using 6,000 small temporary fixture files.

Measures logical-file enumeration, not PNG decoding, hardware throughput, or
industrial capture speed. It never edits an existing project's evidence.
"""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'host'));sys.path.insert(0,str(ROOT/'scripts'))
from workstation import Records
from archive_inventory import inventory,linked
import check_archive

TABLES=('events','review_revisions','pending_confirmation','confirmation_history')


def business_snapshot(database):
    db=sqlite3.connect(database)
    try:
        values={table:sorted(db.execute('SELECT * FROM '+table).fetchall(),key=repr) for table in TABLES}
    finally:db.close()
    wire=json.dumps(values,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return values,hashlib.sha256(wire).hexdigest()


def invoke(root,output):
    run=subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'scripts/check_archive.py'),
                        '--root',str(root),'--output',output],capture_output=True,text=True,encoding='utf-8',timeout=30)
    return run,json.loads(run.stdout)


def directory_link(link,target):
    if os.name=='nt':
        quote=lambda value:"'"+str(value).replace("'","''")+"'"
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
                        'New-Item -ItemType Junction -Path '+quote(link)+' -Target '+quote(target)+' | Out-Null'],
                       check=True,capture_output=True)
    else:os.symlink(target,link,target_is_directory=True)


def main():
    begun=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='tile_v135_capacity_scale_') as temp:
        project=Path(temp)/'project';project.mkdir()
        records=Records(project);archive=records.dir
        rows=[(f'fixture_{i}','2026-09-29T00:00:00Z','needs_recheck' if i%2 else 'pending',
               f'原复核备注 {i}',json.dumps(dict(frame_id=i,reason='fixture'))) for i in range(1000)]
        records.db.executemany('INSERT INTO events VALUES(?,?,?,?,?)',rows)
        records.db.executemany('INSERT INTO review_revisions VALUES(?,?)',[(f'fixture_{i}',i+1) for i in range(0,1000,17)])
        records.db.execute('INSERT INTO pending_confirmation VALUES(1,?)',(json.dumps(dict(retain='pending fixture')),))
        records.db.execute('INSERT INTO confirmation_history(created,status,payload) VALUES(?,?,?)',
                           ('2026-09-29','ACKNOWLEDGED',json.dumps(dict(retain='history fixture'))))
        records.db.commit();records.db.close()
        (project/'host').mkdir();(project/'host/storage_policy.json').write_text(json.dumps(dict(mode='archive',max_archive_mib=64)),encoding='utf-8')
        nested=archive/'staging';nested.mkdir()
        # Deliberately not PNG images: any accidental PNG decoding would fail.
        image=b'capacity fixture, no PNG decode\n'*4;aux=b'bounded auxiliary fixture\n'*5
        for i in range(1000):
            (archive/f'fixture_{i}.png').write_bytes(image)
            (archive/f'fixture_{i}_mask.png').write_bytes(image)
        for i in range(500):
            (archive/f'unindexed_{i}.png').write_bytes(image)
            (archive/f'pending_{i}.png.tmp').write_bytes(aux)
            (nested/f'unindexed_{i}.png').write_bytes(image)
            (nested/f'intent_{i}.json').write_bytes(aux)
        for i in range(2000):(nested/f'part_{i}.bin').write_bytes(aux)
        before,before_hash=business_snapshot(archive/'inspection.sqlite3')
        file_before={p.relative_to(archive).as_posix():p.read_bytes() for p in archive.rglob('*')
                     if p.is_file() and not p.name.startswith('inspection.sqlite3')}
        assert len(file_before)==6000
        # Exercise the production CLI from another interpreter, including the
        # strict reports-only destination and actual JSON/stdout contract.
        cli,cli_result=invoke(project,'v135/scale_cli.json')
        assert cli.returncode==0,(cli.stdout,cli.stderr)
        assert cli_result['capacity_only'] and not cli_result['image_integrity_checked']
        assert cli_result['storage']['max_bytes']==64*1024*1024
        assert Path(cli_result['output_path']).is_relative_to(project/'reports')
        saved_report=Path(cli_result['output_path']).read_bytes()
        for rejected in ('../review_records/do_not_write.json',str(archive/'do_not_write.json'),'v135/scale_cli.json'):
            failed,body=invoke(project,rejected)
            assert failed.returncode==1 and body['status']=='CAPACITY_CHECK_FAILED'
        assert not (archive/'do_not_write.json').exists()
        assert Path(cli_result['output_path']).read_bytes()==saved_report
        report_link=project/'reports'/'redirect';directory_link(report_link,archive)
        try:
            failed,body=invoke(project,'redirect/do_not_write.json')
            assert failed.returncode==1 and not (archive/'do_not_write.json').exists()
        finally:
            assert linked(report_link.lstat()) and report_link.resolve()==archive.resolve()
            if os.name=='nt':os.rmdir(report_link)
            else:report_link.unlink()
        linked_root=Path(temp)/'linked_project';linked_root.mkdir()
        archive_link=linked_root/'review_records';directory_link(archive_link,archive)
        try:
            failed,body=invoke(linked_root,'do_not_write.json')
            assert failed.returncode==1 and not (linked_root/'reports').exists()
        finally:
            assert linked(archive_link.lstat()) and archive_link.resolve()==archive.resolve()
            if os.name=='nt':os.rmdir(archive_link)
            else:archive_link.unlink()
        absent=Path(temp)/'empty_project';absent.mkdir()
        failed,body=invoke(absent,'new.json')
        assert failed.returncode==1 and not (absent/'review_records').exists() and not (absent/'reports').exists()
        # The in-process route must also avoid image decoding/hashing. Only
        # report/file-size metadata is observed by this command.
        with patch('hashlib.sha256',side_effect=AssertionError('CLI hashed image/content')), \
             patch('PIL.Image.open',side_effect=AssertionError('CLI decoded image')):
            direct=check_archive.check(project,'v135/no_image_read.json')
        records=Records(project)
        try:
            timings=[]
            for _ in range(7):
                start=time.perf_counter();snap=records.storage();timings.append((time.perf_counter()-start)*1000)
                assert snap['scan_complete'] and snap['scan_issue_count']==0
                assert snap['unindexed_png_count']==1000 and snap['temp_file_count']==500
                assert snap['image_bytes']==2500*len(image)
                assert snap['auxiliary_bytes']==3000*len(aux)+500*len(image)
                assert snap['used_bytes']==sum(p.stat().st_size for p in archive.rglob('*') if p.is_file())
            limited=inventory(archive,(r[0] for r in rows),max_entries=1000)
            assert not limited['scan_complete'] and limited['file_count']<=1000
            assert any(issue['reason']=='entry_limit' for issue in limited['scan_issues'])
        finally:records.db.close()
        after,after_hash=business_snapshot(archive/'inspection.sqlite3')
        assert before==after and before_hash==after_hash
        assert file_before=={p.relative_to(archive).as_posix():p.read_bytes() for p in archive.rglob('*')
                            if p.is_file() and not p.name.startswith('inspection.sqlite3')}
        result=dict(passed=True,created_at=datetime.now(timezone.utc).isoformat(),
            scope='6,000 temporary regular files; real Records.storage and CLI, no board or image-integrity test',
            fixture=dict(evidence_records=1000,fixture_files=6000,unindexed_png_count=1000,temp_file_count=500,
                         fixture_content_bytes=sum(map(len,file_before.values()))),
            business_records_unchanged=True,business_snapshot_sha256=before_hash,
            business_table_rows={name:len(values) for name,values in before.items()},
            fixture_file_contents_unchanged=True,cli_no_image_hash_or_decode=True,
            cli_rejected_outside_reports=True,cli_refused_existing_report=True,cli_refused_missing_database=True,
            cli_refused_report_and_archive_links=True,
            entry_limit_enforced=dict(limit=1000,file_count=limited['file_count'],scan_complete=limited['scan_complete']),
            storage_scan_ms=dict(samples=timings,min=min(timings),median=statistics.median(timings),max=max(timings)),
            cli_timing_ms=cli_result['timing_ms'],
            duration_seconds=time.perf_counter()-begun,
            source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                           (ROOT/'host/workstation.py',ROOT/'host/archive_inventory.py',ROOT/'scripts/check_archive.py',Path(__file__))})
    out=ROOT/'reports/v135/archive_inventory_scale.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
