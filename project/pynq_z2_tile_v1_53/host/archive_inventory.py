"""Read-only, bounded archive file inventory; never follows reparse points.

Sizes are logical regular-file bytes, not filesystem allocated blocks. The
caller reserves the Records SQLite writer while enumerating, so cooperating
saves cannot appear halfway through publication. No PNG decoding or hashing is
performed here: this is capacity accounting, not an integrity certification.
"""
import os
import re
import stat
from pathlib import Path

MAX_ENTRIES=100000
MAX_DEPTH=64
MAX_ISSUES=20


class ArchiveInventoryError(OSError):
    """Incomplete accounting must stop saving, not trigger quota fallback."""


def linked(attributes):
    return stat.S_ISLNK(attributes.st_mode) or bool(
        getattr(attributes,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400))


def inventory(directory,record_ids,max_entries=MAX_ENTRIES):
    directory=Path(directory)
    result=dict(image_bytes=0,metadata_bytes=0,auxiliary_bytes=0,
                unindexed_png_count=0,temp_file_count=0,file_count=0,
                scan_complete=True,scan_issue_count=0,scan_issues=[])
    def issue(path,reason):
        result['scan_complete']=False;result['scan_issue_count']+=1
        if len(result['scan_issues'])<MAX_ISSUES:
            result['scan_issues'].append(dict(path=path,reason=reason))
    expected=set()
    for key in record_ids:
        if not isinstance(key,str) or re.fullmatch(r'[A-Za-z0-9_]{1,128}',key) is None:
            issue('.','invalid_record_id');continue
        expected.update((os.path.normcase(key+'.png'),os.path.normcase(key+'_mask.png')))
    pending=[(directory,0)];entries=0
    while pending:
        current,depth=pending.pop();relative=current.relative_to(directory).as_posix()
        try:
            attributes=current.lstat()
            if linked(attributes):issue(relative,'link_or_reparse_point');continue
            if not stat.S_ISDIR(attributes.st_mode):issue(relative,'not_a_directory');continue
            if depth>MAX_DEPTH:issue(relative,'directory_depth_limit');continue
            with os.scandir(current) as children:
                for entry in children:
                    entries+=1
                    if entries>max_entries:
                        issue('.','entry_limit');pending.clear();break
                    relative=Path(entry.path).relative_to(directory).as_posix()
                    try:attributes=entry.stat(follow_symlinks=False)
                    except OSError:issue(relative,'stat_unavailable');continue
                    if linked(attributes):issue(relative,'link_or_reparse_point');continue
                    if stat.S_ISDIR(attributes.st_mode):
                        pending.append((Path(entry.path),depth+1));continue
                    if not stat.S_ISREG(attributes.st_mode):issue(relative,'unsupported_file_type');continue
                    result['file_count']+=1
                    name=entry.name.lower();top=depth==0
                    if top and name.endswith('.png'):category='image_bytes'
                    elif top and name.startswith('inspection.sqlite3'):category='metadata_bytes'
                    else:category='auxiliary_bytes'
                    result[category]+=attributes.st_size
                    if name.endswith('.tmp'):result['temp_file_count']+=1
                    # Stored evidence lives at the root. Nested PNGs also count
                    # as unindexed, while their bytes belong to auxiliary data.
                    if name.endswith('.png') and (not top or os.path.normcase(entry.name) not in expected):
                        result['unindexed_png_count']+=1
        except OSError:issue(current.relative_to(directory).as_posix(),'directory_unavailable')
    result['used_bytes']=sum(result[key] for key in ('image_bytes','metadata_bytes','auxiliary_bytes'))
    return result
