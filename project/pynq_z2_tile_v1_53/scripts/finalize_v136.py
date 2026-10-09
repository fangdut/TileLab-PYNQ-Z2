"""Seal a tested display-only capacity optimization; no formal report."""
from pathlib import Path
import argparse,datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v136';W=R/(R.name+'.sdk')
STATUS='BOARD_VALIDATED_DISPLAY_STORAGE_SNAPSHOT'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def hashes(root,values):
    assert values
    for p,h in values.items():assert sha(root/p)==h,('Changed source or proof',str(root/p))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check-only',action='store_true');a=ap.parse_args()
    plan=load(R/'ITERATION_PLAN.json');B=Path(plan['baseline']);old=load(B/'DELIVERY_MANIFEST.json')
    assert B.name=='pynq_z2_tile_v1_35' and sha(B/'DELIVERY_MANIFEST.json')==plan['baseline_manifest_sha256']
    for group in ('source_sha256','proof_sha256'):hashes(B,old[group])
    assert sha(Path(plan['backup']))==plan['backup_sha256'];hashes(W,plan['inherited_hardware_sha256'])
    s=load(O/'validation_summary.json');assert s['passed'] and s['version']=='V1.36'
    assert s['unit_tests']['passed'] and s['unit_tests']['count']>309
    audit=s['source_audit'];assert audit['passed'] and audit['unchanged_pl_firmware_files']==98
    hashes(R,audit['unchanged_sources_sha256']);hashes(R,audit['host_source_sha256'])
    for name in ('review_ui','preview_ui','inventory_ui'):
        u=s[name];assert u['passed'] and all(c['passed'] for c in u['cases'])
        if 'html_sha256' in u:assert sha(R/'host/workstation.html')==u['html_sha256']
    assert sha(R/'host/review_session.js')==s['review_ui']['session_source_sha256']
    assert s['tcp_load']['passed'];hashes(R,s['tcp_load']['source_sha256'])
    process=s['storage_process'];assert process['passed'] and all(c['passed'] for c in process['cases'])
    mapping={'baseline/workstation.py':R.parent/'pynq_z2_tile_v1_34/host/workstation.py','current/workstation.py':R/'host/workstation.py','current/archive_inventory.py':R/'host/archive_inventory.py','test_script':R/'scripts/test_storage_rollback_process.py'}
    for k,p in mapping.items():assert sha(p)==process['source_sha256'][k]
    perf=load(O/'storage_snapshot_http/summary.json');assert perf['passed']
    assert sha(R/'scripts/test_storage_snapshot_http.py')==perf['script_sha256']
    compact=[]
    for c in perf['cases']:
        assert c['passed'] and c['http_requests']==30 and c['all_fixture_file_hashes_unchanged']
        hashes(Path(c['source_root']),c['source_sha256'])
        compact.append({k:c[k] for k in ('case','http_requests','inventory_scans','http_latency_ms','fixture_business_rows','fixture_ordinary_files_excluding_database')})
    by={c['case']:c for c in compact};assert len(by)==3
    assert by['baseline_native']['inventory_scans']==30 and by['candidate_forced_fresh']['inventory_scans']==30
    assert by['candidate_native']['inventory_scans']<=3
    board=load(O/'board_preview_rates/summary.json');assert board['passed'] and board['revision']=='V1.36' and not board['cleanup_errors']
    hashes(R,board['source_sha256']);assert len(board['cases'])==1
    case=board['cases'][0];assert case['passed'] and case['preview_rate_fps']==2 and case['saved_events']>=8
    assert len(case['checks'])==case['saved_events']==case['defective_products_delta']
    assert all(c['passed'] for c in case['checks']) and all(n==0 for n in case['error_deltas'].values())
    assert case['after']['depth']==0 and not case['final_state']['pending_operation']
    program=load(R/'reports/programmed_v136.json');ready=load(O/'boot_readiness.json')
    assert program['boot_id']==ready['state']['boot_id']==board['boot_id'] and ready['passed']
    assert board['firmware_version']==ready['state']['version']==0x12000
    hashes(W,program['sha256'])
    assert all(plan['inherited_hardware_sha256'][k]==v for k,v in program['sha256'].items())
    if a.check_only:print(json.dumps(dict(passed=True,writes=False)));return
    s.update(status=STATUS,scope='Display capacity snapshots; fresh save admission; physical HDMI/PL/TCP regression',
             storage_http=dict(path='reports/v136/storage_snapshot_http/summary.json',sha256=sha(O/'storage_snapshot_http/summary.json'),cases=compact),
             board_test=dict(performed=True,passed=True,path='reports/v136/board_preview_rates/summary.json',sha256=sha(O/'board_preview_rates/summary.json'),boot_id=board['boot_id'],host_captures=case['host_captures'],saved_events=case['saved_events'],error_deltas=case['error_deltas']))
    s['limits']=['The display snapshot can lag external file changes by five seconds; save admission always rescans.','Fresh scans and actual saves still take time; this is not a claim that every control operation is wait-free.','HTTP fixture timings do not measure physical Ethernet throughput.','Repeated real photographs with synthetic motion are engineering regression, not independent factory accuracy.','PL and ARM remain byte-identical to V1.32; finite queues and physical power-loss limits remain.']
    save(O/'validation_summary.json',s)
    before=by['baseline_native'];after=by['candidate_native']
    (R/'README.md').write_text(f'''# TileLab V1.36

状态：{STATUS}。

本版只优化电脑端状态查询：容量展示复用最多 5 秒的盘点，显示年龄、陈旧/失败状态；目录遍历与复核列表读取移出 Station 控制锁。新存档、容量设置仍实时清点，保存成功或失败都会使展示快照失效。FPGA 与 ARM 算法/固件保持已验收版本，未提高或改变识别精度。

验证：{s['unit_tests']['count']} 项主机、{sum(s[n]['tests'] for n in ('review_ui','preview_ui','inventory_ui'))} 项前端测试通过；独立进程中断/回滚与真实回环 TCP 回归通过。6000 文件、1000 记录、3 个模拟窗口的 10 秒 HTTP 对照：30 次查询的扫描次数从 {before['inventory_scans']} 降至 {after['inventory_scans']}，延迟中位数从 {before['http_latency_ms']['median']:.2f} ms 降至 {after['http_latency_ms']['median']:.2f} ms。这是电脑端夹具测量。实板默认 2 fps 下连续运行 {case['seconds']:.2f} 秒，接收 {case['host_captures']} 帧、保留 {case['saved_events']} 个缺陷产品；逐图掩码、框和 CRC 一致，相关错误计数增量为 0。

工程：打开 `{R.name}.xpr`；Vitis 工作区 `{W.name}`。启动 `启动以太网工作站.bat`；测试证据在 `reports/v136/validation_summary.json`。运行中的检测仍全在 FPGA；离线参考模型只用于验证。

回退：V1.35 原工程保持不变，源码与下载文件备份 `{Path(plan['backup']).as_posix()}`。历史素材/运行证据保留在原根，轻量 ZIP 不是整盘备份。

边界：盘点缓存仅代表观察时刻；保存及数据库操作仍可能等待，PNG 与 SQLite 不构成统一断电事务。下一步继续以正常纹理误报门禁评估弱裂纹算法，不以放松门槛换取表面召回提升。本版不生成单独正式报告，批量迭代后再汇总。
''',encoding='utf-8')
    (R/'host/benchmark.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>V1.36 验证记录</title><style>body{font:16px/1.8 system-ui;max-width:1050px;margin:40px auto;background:#eef5f5;color:#183749}main{background:white;padding:32px;border-radius:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}</style><main><a href="/">返回工作站</a><h1>V1.36 · 容量查询提速</h1><p>页面复用最近盘点；新存档始终重新清点。测试数据区分临时目录 HTTP 性能和实板接收回归；不代表新的工业检测精度。</p><pre id="r">读取中</pre></main><script>fetch('/api/benchmark').then(r=>{if(!r.ok)throw Error('读取失败');return r.json()}).then(s=>document.querySelector('#r').textContent=JSON.stringify({version:s.version,status:s.status,unit_tests:s.unit_tests,storage_http:s.storage_http,board_test:s.board_test,limits:s.limits},null,2)).catch(e=>document.querySelector('#r').textContent=e.message)</script></html>''',encoding='utf-8')
    plan.update(phase='VALIDATED_BOARD',scope='HOST_CHANGES_WITH_PHYSICAL_BOARD_REGRESSION',hardware='Byte-identical V1.32 PL/ARM; V1.36 physical-board regression completed');save(R/'ITERATION_PLAN.json',plan)
    sources={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources'):
        for p in (R/folder).rglob('*'):
            if p.is_file() and not any(x in ('__pycache__','runtime') for x in p.parts) and p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):sources[p.relative_to(R).as_posix()]=sha(p)
    for p in W.iterdir():
        if p.is_file() and p.suffix in ('.py','.tcl','.bat'):sources[p.relative_to(R).as_posix()]=sha(p)
    proofs=['README.md','ITERATION_PLAN.json','reports/timing_summary.rpt','reports/programmed_v136.json']+[p.relative_to(R).as_posix() for p in O.rglob('*') if p.is_file() and p.suffix in ('.json','.log')]
    size=0
    for parent,dirs,files in os.walk(R,followlinks=False):
        dirs[:]=[d for d in dirs if not (Path(parent)/d).is_symlink() and not (Path(parent)/d).is_junction()]
        size+=sum((Path(parent)/f).stat().st_size for f in files)
    save(R/'DELIVERY_MANIFEST.json',dict(version='V1.36',status=STATUS,created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseline=str(B),backup=plan['backup'],backup_sha256=plan['backup_sha256'],hardware_revision=plan['hardware'],inherited_artifacts_sha256=plan['inherited_hardware_sha256'],source_sha256=sources,proof_sha256={p:sha(R/p) for p in sorted(set(proofs))},validation=s,size_bytes=size,report='README.md',limits=s['limits']))
    p=R.parent/'TileLab_进度与回退.md';t=p.read_text(encoding='utf-8');i=t.index('更新：');j=t.index('## 当前产品')
    t=t[:i]+f'更新：{datetime.datetime.now().astimezone().isoformat()}\n\n最新软件与实板验收：**V1.36**。容量展示缓存与保存准入分离；HTTP 性能、故障回归和实板连续运动验收通过。PL/ARM 仍保持 V1.32。按用户要求，仅保存逐版简短说明，批量后汇总报告。\n\n'+t[j:]
    t=t.replace('## 尚在进行',f'| V1.36 | 展示盘点缓存、控制锁占用减少、准入实时盘点保留 | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i=t.index('## 尚在进行');j=t.index('## 回退和空间');t=t[:i]+'## 尚在进行\n\nV1.36 已封存。下一步在独立实验中检验弱裂纹改进假设，先检查正常图误报，不直接替换当前板端算法。\n\n'+t[j:];p.write_text(t,encoding='utf-8')
    print(json.dumps(dict(version='V1.36',status=STATUS,tests=s['unit_tests']['count'],size_mib=round(size/1024**2,2))))
if __name__=='__main__':main()
