"""Coordinated archive capacity inventory; never edits business records.

This is not a byte-for-byte read-only SQLite open: Records may run compatible
CREATE IF NOT EXISTS statements and SQLite may recover/update WAL side files.
The inventory takes the same writer reservation as a cooperating evidence save.
No images are decoded/hashed, no evidence is repaired/deleted, and no board or
Station is started. JSON output is restricted to this project's reports tree.
"""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

sys.dont_write_bytecode=True
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'host'))
from archive_inventory import linked
from storage_policy import StoragePolicy
from workstation import Records


def refuse_link(path):
    try:attributes=path.lstat()
    except FileNotFoundError:return
    if linked(attributes):raise ValueError(f'拒绝目录链接/重解析点：{path}')


def checked_paths(root,output=None):
    root=Path(root).resolve(strict=True)
    if not root.is_dir():raise ValueError('工程根目录不是文件夹')
    archive=root/'review_records';refuse_link(archive)
    database=archive/'inspection.sqlite3';refuse_link(database)
    if not database.is_file():raise ValueError('没有已有 inspection.sqlite3；不会新建存档数据库')
    reports=root/'reports';refuse_link(reports)
    if output is None:
        output='v135/archive_check_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')+'.json'
    output=Path(output)
    candidate=output if output.is_absolute() else reports/output
    # Normalize dot components before creating any directory. Check both the
    # lexical boundary and every existing path component for reparse points.
    candidate=Path(os.path.abspath(candidate))
    try:relative=candidate.relative_to(reports)
    except ValueError:raise ValueError('输出路径必须位于该工程 reports 目录内') from None
    if candidate.suffix.lower()!='.json' or not relative.parts:raise ValueError('输出文件必须使用 .json 扩展名')
    current=reports
    for part in relative.parts:
        current=current/part;refuse_link(current)
    if candidate.exists():raise ValueError('输出文件已经存在；请使用新文件名保留原报告')
    if not candidate.resolve().is_relative_to(reports.resolve()):raise ValueError('输出解析后越出 reports 目录')
    return root,archive,candidate


def check(root=PROJECT,output=None):
    root,archive,output=checked_paths(root,output)
    policy=StoragePolicy(root)  # Read existing settings; never writes defaults.
    started=time.perf_counter();records=None
    try:
        records=Records(root)
        records.max_archive_bytes=policy.max_bytes
        initialized=time.perf_counter()
        snapshot=records.storage()
        finished=time.perf_counter()
    finally:
        if records is not None:records.db.close()
    result=dict(schema='TILE_ARCHIVE_CAPACITY_CHECK_V1',project_root=str(root),
        archive_path=str(archive),created_at=datetime.now(timezone.utc).isoformat(),
        output_path=str(output),capacity_only=True,image_integrity_checked=False,
        status='CAPACITY_SCAN_COMPLETE' if snapshot['scan_complete'] else 'CAPACITY_SCAN_INCOMPLETE',
        sqlite_open_mode='Records compatible initialization and coordinated BEGIN IMMEDIATE inventory',
        business_records_modified=False,
        caveats=[
            '只清点逻辑文件字节，不检查 PNG 解码、图像哈希、缺失证据或检测准确率。',
            '不修改业务记录、不恢复、不删除、不确认板端事件；未启动 Station 或硬件连接。',
            '不是数据库字节级只读：兼容表/索引初始化和 SQLite WAL 恢复可能改变数据库结构或元文件。',
            '未索引 PNG 或临时文件仅为分类结果，不代表可以直接删除。',
            '快照与采用同一 SQLite 写事务的保存操作协调；无法阻止外部程序直接改动文件。',
            'SQLite 连接关闭可能归并 WAL，报告中的元数据大小是清点时刻的值。'],
        timing_ms=dict(records_initialization=(initialized-started)*1000,
                       explicit_inventory=(finished-initialized)*1000,total=(finished-started)*1000),
        storage=snapshot)
    # checked_paths validated the destination before Records was opened. Use
    # exclusive creation, so neither an old report nor evidence is overwritten.
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as handle:
        json.dump(result,handle,ensure_ascii=False,indent=2);handle.write('\n')
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default=str(PROJECT),help='已有工程根目录；必须已有 review_records/inspection.sqlite3')
    parser.add_argument('--output',help='reports 内的相对路径，或仍位于该 reports 内的绝对 .json 路径；不覆盖已有文件')
    args=parser.parse_args(argv)
    try:
        result=check(args.root,args.output)
    except (OSError,ValueError,sqlite3.Error) as error:
        failure=dict(status='CAPACITY_CHECK_FAILED',capacity_only=True,image_integrity_checked=False,error=str(error))
        print(json.dumps(failure,ensure_ascii=False,indent=2))
        print('存档容量清点未完成：'+str(error),file=sys.stderr)
        return 1
    s=result['storage']
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print(('存档容量清点完成' if s['scan_complete'] else '存档容量清点不完整')+
          f"：{s['file_count']} 个普通文件，{s['used_bytes']/1048576:.3f} MiB；"+
          f"未索引 PNG {s['unindexed_png_count']} 个，临时文件 {s['temp_file_count']} 个。"+
          '本次没有检查图像完整性，也没有删除或恢复任何证据。\nJSON：'+result['output_path'],file=sys.stderr)
    return 0 if s['scan_complete'] else 2


if __name__=='__main__':raise SystemExit(main())
