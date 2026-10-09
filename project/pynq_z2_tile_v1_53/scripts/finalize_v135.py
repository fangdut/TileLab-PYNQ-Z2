"""Seal V1.35 only after host and physical-board evidence passes current hashes.

Writes a short README, benchmark page, manifest and global progress entry. It
does not program hardware, start services, delete evidence, or produce a PDF.
Use --check-only to validate every gate without changing release documents.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os

R=Path(__file__).resolve().parents[1]
O=R/'reports/v135'
W=R/(R.name+'.sdk')
STATUS='BOARD_VALIDATED_ARCHIVE_INVENTORY_AND_PREVIEW_BUDGET'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def ensure(condition,message):
    if not condition:raise RuntimeError(message)


def check_sources(root,values,label):
    ensure(bool(values),label+' has no source hashes')
    for relative,expected in values.items():
        path=root/relative
        ensure(path.is_file() and sha(path)==expected,label+' source changed: '+relative)


def validate():
    plan=load(R/'ITERATION_PLAN.json');base=Path(plan['baseline'])
    ensure(base.name=='pynq_z2_tile_v1_34','Baseline must be the sealed V1.34 root')
    ensure(sha(base/'DELIVERY_MANIFEST.json')==plan['baseline_manifest_sha256'],'Baseline manifest changed')
    old=load(base/'DELIVERY_MANIFEST.json')
    for group in ('source_sha256','proof_sha256'):check_sources(base,old[group],'V1.34 '+group)
    ensure(sha(Path(plan['backup']))==plan['backup_sha256'],'V1.34 backup hash mismatch')
    summary=load(O/'validation_summary.json')
    ensure(summary['passed'] is True and summary['version']=='V1.35','Host validation did not pass V1.35')
    tests=load(O/'host_tests.json')
    ensure(tests==summary['unit_tests'] and tests['passed'] is True and tests['count']==309
           and not tests['errors'] and not tests['failures'],'Expected 309 passing current host tests')
    for key,name,count in (('review_ui','review_session_native.json',19),
                           ('preview_ui','preview_ui_native.json',11),
                           ('inventory_ui','inventory_ui_native.json',4)):
        evidence=load(O/name)
        ensure(evidence==summary[key] and evidence['passed'] is True and evidence['tests']==count,
               'UI validation mismatch: '+name)
        ensure(all(case['passed'] is True for case in evidence['cases']),'UI case failed: '+name)
        if 'html_sha256' in evidence:
            ensure(sha(R/'host/workstation.html')==evidence['html_sha256'],'Workstation HTML changed after '+name)
    ensure(sha(R/'host/review_session.js')==summary['review_ui']['session_source_sha256'],'Review JS changed')
    tcp=load(O/'preview_tcp_load/summary.json')
    ensure(tcp==summary['tcp_load'] and tcp['passed'] is True,'Loopback evidence mismatch')
    check_sources(R,tcp['source_sha256'],'Loopback')
    process=load(O/'storage_rollback_process/summary.json')
    ensure(process==summary['storage_process'] and process['passed'] is True,'Process-exit evidence mismatch')
    mapping={'baseline/workstation.py':base/'host/workstation.py',
             'current/workstation.py':R/'host/workstation.py',
             'current/archive_inventory.py':R/'host/archive_inventory.py',
             'test_script':R/'scripts/test_storage_rollback_process.py'}
    ensure(set(process['source_sha256'])==set(mapping),'Unexpected process evidence hash schema')
    for name,path in mapping.items():ensure(sha(path)==process['source_sha256'][name],'Process test source changed: '+name)
    ensure(all(case['passed'] is True for case in process['cases']),'A process-exit case failed')
    scale=load(O/'archive_inventory_scale.json')
    ensure(scale['passed'] is True and scale['fixture']['fixture_files']==6000,'6,000-file capacity validation missing')
    for name in ('business_records_unchanged','fixture_file_contents_unchanged','cli_no_image_hash_or_decode',
                 'cli_rejected_outside_reports','cli_refused_existing_report','cli_refused_missing_database',
                 'cli_refused_report_and_archive_links'):
        ensure(scale[name] is True,'Capacity CLI validation failed: '+name)
    check_sources(R,scale['source_sha256'],'Capacity scale test')
    source=load(O/'source_audit.json')
    ensure(source==summary['source_audit'] and source['passed'] is True,'Source audit mismatch')
    unchanged={}
    for folder in ('rtl','constraints','ip_repo'):
        for p in (base/folder).rglob('*'):
            if p.is_file():
                relative=p.relative_to(base).as_posix();unchanged[relative]=sha(p)
    base_workspace=base/(base.name+'.sdk')
    for p in (base_workspace/'ethernet_sources').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            relative=(Path(W.name)/p.relative_to(base_workspace)).as_posix();unchanged[relative]=sha(p)
    ensure(len(unchanged)==98 and source['unchanged_pl_firmware_files']==98,'Expected 98 inherited PL/ARM source files')
    ensure(unchanged==source['unchanged_sources_sha256'],'Inherited source file set changed')
    check_sources(R,unchanged,'Inherited PL/ARM')
    ensure(plan['inherited_hardware_sha256']==old['inherited_artifacts_sha256']==source['inherited_artifacts_sha256'],
           'Hardware artifact chain differs from V1.34')
    check_sources(W,plan['inherited_hardware_sha256'],'Inherited BIT/XSA/LTX/ELF')
    ensure(sha(R/'reports/timing_summary.rpt')==sha(base/'reports/timing_summary.rpt'),'Inherited timing report changed')
    ensure((R/(R.name+'.xpr')).is_file() and (R/(R.name+'.srcs')/'sources_1/bd/system/system.bd').is_file(),
           'Vivado project/Block Design missing')
    prepared=(O/'prepare_project.log').read_text(encoding='utf-8',errors='replace')
    ensure('Exiting Vivado' in prepared and '\nERROR:' not in prepared,'Project preparation did not finish cleanly')

    board=load(O/'board_preview_rates/summary.json')
    ensure(board['passed'] is True and board['revision']=='V1.35','Physical-board V1.35 comparison has not passed')
    ensure(board['firmware_version']==0x12000,'Unexpected physical-board firmware')
    ensure(len(board['cases'])==3 and {case['preview_rate_fps'] for case in board['cases']}=={0,5,2},
           'Physical-board evidence must contain exactly 0/5/2 fps cases')
    check_sources(R,board['source_sha256'],'Physical-board comparison')
    ensure(board['program_proof']=='reports/programmed_v135.json','Wrong board programming proof path')
    ensure(board['ready_proof']=='reports/v135/boot_readiness.json','Wrong boot readiness proof path')
    program=load(R/board['program_proof']);ready=load(R/board['ready_proof'])
    ensure(program['active_application']=='hdmi_ethernet','Wrong downloaded application')
    ensure(program['boot_id']==ready['state']['boot_id']==board['boot_id'],'Board boot identity changed between proofs')
    ensure(ready['passed'] is True and ready['state']['version']==0x12000 and ready['state']['capture_health']['ready'],
           'Boot readiness/firmware proof failed')
    for relative,expected in program['sha256'].items():
        ensure(relative in plan['inherited_hardware_sha256'] and expected==plan['inherited_hardware_sha256'][relative],
               'Programming proof artifact differs: '+relative)
        ensure(sha(W/relative)==expected,'Downloaded artifact changed: '+relative)
    ensure(set(program['sha256'])=={'system.bit','system.xsa','hdmi_ethernet/build/hdmi_ethernet.elf'},
           'Programming proof artifact set incomplete')
    for case in board['cases']:
        label=str(case['preview_rate_fps'])+' fps'
        ensure(case.get('passed') is True,'Board case did not pass: '+label)
        ensure(case['seconds']>0 and case['video_seconds']>0 and case['received_bytes_delta']>0
               and case['requests_delta']>0 and case['host_captures']>0 and case['saved_events']>0,
               'Board case missing measured activity: '+label)
        ensure(case['before']['boot_id']==case['after']['boot_id']==board['boot_id'],'Board rebooted during '+label)
        ensure(case['before']['version']==case['after']['version']==board['firmware_version'],'Firmware changed during '+label)
        ensure(case['error_deltas'] and all(value==0 for value in case['error_deltas'].values()),'Board errors increased in '+label)
        ensure(case['checks'] and len(case['checks'])==case['saved_events'],
               'Board evidence count differs from per-image checks in '+label)
        for checked in case['checks']:
            ensure(checked['passed'] is True and checked['mask_mismatch']==0,
                   'Board image mask comparison failed in '+label)
            for key in ('boxes_match','areas_match','overflow_match','candidate_area_match',
                        'full_tile','crc3','captured_quad_threshold_90','source_label_is_crack'):
                ensure(checked[key] is True,'Board image check failed: '+label+' '+key)
        ensure(case['defective_products_delta']==case['saved_events'],'Board alarm/save counts differ in '+label)
        ensure(case['after']['depth']==0 and not case['final_state']['pending_operation']
               and not case['final_state']['pending_confirmation'],'Board queue or confirmation not drained in '+label)
    ensure(not board.get('cleanup_errors'),'Board test cleanup failed')
    return plan,base,old,summary,board,program,ready,scale


def collect_sources():
    sources={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources'):
        for p in sorted((R/folder).rglob('*')):
            if p.is_file() and not any(x in ('__pycache__','runtime') for x in p.parts) and p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):
                sources[p.relative_to(R).as_posix()]=sha(p)
    for p in W.iterdir():
        if p.is_file() and p.suffix in ('.py','.tcl','.bat'):sources[p.relative_to(R).as_posix()]=sha(p)
    return sources


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args(argv)
    plan,base,old,summary,board,program,ready,scale=validate()
    if args.check_only:
        print(json.dumps(dict(passed=True,version='V1.35',status=STATUS,boot_id=board['boot_id'],writes=False)))
        return
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    cases=sorted(board['cases'],key=lambda case:{0:0,5:1,2:2}[case['preview_rate_fps']])
    labels={0:'不限',5:'5 fps',2:'2 fps'}
    table=['| 普通预览上限 | 测量窗（秒，含排空） | 主机取图 | 留存事件 | 接收量（MB） |',
           '|---|---:|---:|---:|---:|']
    for case in cases:
        table.append(f"| {labels[case['preview_rate_fps']]} | {case['seconds']:.3f} | {case['host_captures']} | {case['saved_events']} | {case['received_bytes_delta']/1e6:.3f} |")
    summary.update(status=STATUS,scope='V1.35 host archive capacity and 0/5/2 fps physical-board preview/event regression; PL and ARM firmware inherited byte-for-byte from V1.32',
                   sealed_at=now,archive_inventory_scale=scale,
                   board_test=dict(performed=True,passed=True,summary_path='reports/v135/board_preview_rates/summary.json',
                                   boot_id=board['boot_id'],firmware_version=board['firmware_version'],results=board),
                   boot_readiness=ready,programming_proof=program)
    summary['limits']=[
        'Physical testing uses computer-generated HDMI replay through PYNQ-Z2; it does not establish real-camera or factory inspection accuracy.',
        '0/5/2 fps limits ordinary host previews, not FPGA detection; retained events and manual captures bypass the preview budget.',
        'Inventory measures regular-file logical lengths; it does not verify image hashes, PNG decoding, missing images or allocated NTFS blocks.',
        'Incomplete inventory blocks new archival. Orphans and temporary files are preserved, never automatically deleted or recovered.',
        'Snapshot coordination covers cooperating SQLite writers; uncontrolled external filesystem modification is outside that guarantee.',
        'Process-exit/rollback tests do not establish physical power-loss safety; PNG and SQLite are not one crash-atomic transaction.',
        'The bounded board queue cannot retain all events indefinitely during receiver outages or board power loss.',
        'Capacity CLI can run compatible SQLite initialization/WAL maintenance; business records are not edited, but database-file bytes may change.',
        'The 6,000-file capacity timing is a host fixture measurement, not FPGA or Ethernet throughput.'
    ]
    write_json(O/'validation_summary.json',summary)
    readme=f'''# TileLab V1.35

状态：**{STATUS}**。本版改善电脑端存档容量统计，并完成预览不限/5/2 fps 的新实板对照。FPGA 裂纹检测、ARM 传输源码共 98 个文件及 BIT/XSA/LTX/ELF 与已验收基线保持逐字节一致，固件仍为 `0x12000`；本次板卡启动号 `{board['boot_id']}`。

存档容量现在包括未登记 PNG、临时文件、嵌套辅助文件和 SQLite 元文件。清点与配合使用 SQLite 写事务的保存操作协调；遇到不可读文件、目录链接或清点限额时阻止新增存档，保留原证据。界面显示清点状态、辅助文件占用及未索引/临时文件数量。

普通预览默认上限 2 fps，可选 5 或不限；报警队列、人工抓拍、待确认恢复优先。空队列约每 200 ms 检查状态，实际还包含操作系统、网络及处理耗时。档位是服务会话设置，重启恢复默认值；FPGA 检测速度不由这个档位决定。

本次实板对照：

{chr(10).join(table)}

各档实测错误计数增量与验收检查见 [实板完整证据](reports/v135/board_preview_rates/summary.json)。接收量是测量窗内协议累计字节，不能直接当成网口极限吞吐；照片回放的重复产品也不等于独立工业样本。这里不宣称新的识别精度。

软件验证：309 项主机、19 项复核 JS、11 项预览 JS、4 项存档界面 JS 通过；生产接收链路的真实回环 TCP、独立进程保存中断与回滚、6,000 个文件容量清点通过。容量扫描中位 `{scale['storage_scan_ms']['median']:.2f} ms`，最大 `{scale['storage_scan_ms']['max']:.2f} ms`；业务记录、复核备注/修订、待确认与历史记录保持不变。详见 [验收汇总](reports/v135/validation_summary.json)。

容量体检：运行 `scripts/check_archive.py --root "{R.as_posix()}"`。JSON 只能输出到所选工程 `reports` 内，不覆盖旧报告；不会启动 Station 或连接开发板，不删除、不恢复、不 ACK。该命令只清点文件长度，不做图像哈希/PNG 解码，也不检查缺失图像；SQLite 兼容初始化及 WAL 处理可能改变元文件，因此不是数据库字节级只读。

工程入口：`{R.name}.xpr`；Vitis 工作区为 `{W.name}`，必要时执行 `build_ethernet.py` 生成 BSP。下载用 `.sdk/program_ethernet.bat`，电脑界面用 `启动以太网工作站.bat`；同一开发板只运行一个接收程序。默认仅预览，自动存档有容量上限。

回退：原工程 [V1.34]({base.as_posix()}/README.md) 保持封存；轻量备份 `{Path(plan['backup']).as_posix()}`。旧工程的全部运行数据不能由轻量 ZIP 替代。

下一步：减少网页状态轮询对目录的重复扫描，同时保留保存前的权威容量检查；继续改进弱裂纹及跨材质泛化，完善真实相机/现场数据验证。有限队列、掉电前未传出事件和 PNG/SQLite 非统一断电事务仍是边界。

按用户要求，本版仅保留简短摘要和测试证据，批量迭代后统一整理正式报告。
'''
    (R/'README.md').write_text(readme,encoding='utf-8')
    heading='<tr><th>普通预览上限</th><th>测量秒数</th><th>主机取图</th><th>留存事件</th><th>接收 MB</th></tr>'
    rows=''.join(f"<tr><td>{labels[c['preview_rate_fps']]}</td><td>{c['seconds']:.3f}</td><td>{c['host_captures']}</td><td>{c['saved_events']}</td><td>{c['received_bytes_delta']/1e6:.3f}</td></tr>" for c in cases)
    benchmark='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>V1.35 验证记录</title><style>body{font:16px/1.8 system-ui;background:#eef5f5;color:#183749;max-width:1100px;margin:40px auto}main{background:white;padding:36px;border-radius:18px}h1,a{color:#087e85}table{border-collapse:collapse;width:100%;margin:24px 0}th,td{text-align:left;border-bottom:1px solid #dce6e8;padding:10px}pre{font:13px/1.7 monospace;white-space:pre-wrap;overflow-wrap:anywhere}</style><main><a href="/">← 返回工作站</a><h1>V1.35 · 存档容量与报警优先预览</h1><p>309 项主机、34 项前端逻辑测试通过，已完成 PYNQ-Z2 的不限/5/2 fps 实板对照。PL 与 ARM 源码及下载产物继承已验收版本，没有新增视觉算法。</p><table>'''+heading+rows+'''</table><p>测量窗含事件排空；接收量不是链路极限吞吐。使用电脑 HDMI 照片回放，不能据此宣称真实相机流水线精度。普通预览限速不限制 FPGA 检测，报警及人工抓拍优先。</p><p>存档清点包含未登记图片、临时及辅助文件；清点不完整时保留证据并阻止新增存档。容量统计不等同图像完整性检查，不会自动删除或恢复文件。</p><pre id="result">读取证据摘要中</pre></main><script>fetch('/api/benchmark').then(r=>{if(!r.ok)throw Error('读取验证记录失败');return r.json()}).then(s=>document.querySelector('#result').textContent=JSON.stringify({version:s.version,status:s.status,unit_tests:s.unit_tests,archive_inventory_scale:s.archive_inventory_scale,board_test:s.board_test,limits:s.limits},null,2)).catch(e=>document.querySelector('#result').textContent=e.message)</script></html>'''
    (R/'host/benchmark.html').write_text(benchmark,encoding='utf-8')
    plan.update(phase='VALIDATED_BOARD',scope='HOST_CHANGES_WITH_PHYSICAL_BOARD_REGRESSION',
                hardware='Inherited V1.32 PL and ARM firmware byte-for-byte; V1.35 physical-board host regression completed',
                board_boot_id=board['boot_id'],board_validation='reports/v135/board_preview_rates/summary.json')
    write_json(R/'ITERATION_PLAN.json',plan)
    sources=collect_sources()
    proofs=['README.md','ITERATION_PLAN.json','reports/timing_summary.rpt',board['program_proof']]
    proofs += [p.relative_to(R).as_posix() for p in O.rglob('*') if p.is_file() and p.suffix in ('.json','.log')]
    size=0
    for base_path,dirs,files in os.walk(R,followlinks=False):
        dirs[:]=[name for name in dirs if not (Path(base_path)/name).is_symlink() and not (Path(base_path)/name).is_junction()]
        size+=sum((Path(base_path)/name).stat().st_size for name in files)
    manifest=dict(version='V1.35',status=STATUS,created_at=now,baseline=str(base),backup=plan['backup'],
        backup_sha256=plan['backup_sha256'],hardware_revision=plan['hardware'],
        inherited_artifacts_sha256=plan['inherited_hardware_sha256'],source_sha256=sources,
        proof_sha256={name:sha(R/name) for name in sorted(set(proofs))},validation=summary,
        size_bytes=size,report='README.md',limits=summary['limits'])
    write_json(R/'DELIVERY_MANIFEST.json',manifest)
    progress=R.parent/'TileLab_进度与回退.md';text=progress.read_text(encoding='utf-8')
    previous_rows=[line for line in text.splitlines() if line.startswith('| V1.') and not line.startswith('| V1.35 |')]
    start=text.index('更新：');end=text.index('## 当前产品')
    text=text[:start]+f"更新：{datetime.datetime.now().astimezone().isoformat()}\n\n最新软件与实板验收版本：**V1.35**。存档容量清点与不限/5/2 fps 预览对照通过；309 项主机、34 项前端、回环 TCP、进程故障及实板验证已记录。PL 与 ARM 保持 V1.32 已验收源码及下载文件，未声称新的识别精度。\n\n用户要求持续小步迭代，逐版备份和测试；不逐版制作正式报告，批量完成后汇总。\n\n"+text[end:]
    row=f'| V1.35 | 存档完整容量清点、只读业务体检、预览三档实板对照 | {STATUS} | [摘要]({R.as_posix()}/README.md) |'
    old_row=next((line for line in text.splitlines() if line.startswith('| V1.35 |')),None)
    if old_row:text=text.replace(old_row,row,1)
    else:text=text.replace('## 尚在进行',row+'\n\n## 尚在进行',1)
    start=text.index('## 尚在进行');end=text.index('## 回退和空间')
    text=text[:start]+'## 尚在进行\n\nV1.35 已封存。下一步优先减少网页容量状态的重复全目录扫描，同时保持保存前准确清点与异常时保留证据。\n\n'+text[end:]
    text=text.replace('本轮以分版本增补报告记录新的变化。','本轮逐版保存简短摘要与测试证据，按用户新要求在批量迭代后统一整理报告。')
    ensure(all(line in text.splitlines() for line in previous_rows),'A previous version row/link was changed')
    progress.write_text(text,encoding='utf-8')
    print(json.dumps(dict(version='V1.35',status=STATUS,boot_id=board['boot_id'],source_files=len(sources),
                         proof_files=len(manifest['proof_sha256']),size_mib=round(size/1024**2,2))))


if __name__=='__main__':main()
