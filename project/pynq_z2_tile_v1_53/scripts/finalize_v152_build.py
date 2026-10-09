"""Seal V1.52 build evidence; board programming is explicitly pending."""
from pathlib import Path
import datetime,hashlib,json,os,urllib.request
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_51';P=R.parent/'pynq_z2_tile_v1_48';O=R/'reports/v152';W=R/(R.name+'.sdk')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def check(p,h):assert sha(p)==h,('Changed',str(p))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def files(root):
    for parent,ds,ns in os.walk(root,followlinks=False):
        ds[:]=[n for n in ds if n not in ('__pycache__','runtime','review_records') and not (Path(parent)/n).is_symlink() and not (Path(parent)/n).is_junction()]
        for n in ns:
            p=Path(parent)/n
            if not p.is_symlink():yield p
def main():
    assert not (R/'DELIVERY_MANIFEST.json').exists(),'Never rewrite a sealed version'
    plan=load(R/'ITERATION_PLAN.json');assert plan['version']=='V1.52'
    check(B/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);check(plan['backup'],plan['backup_sha256'])
    for n,h in plan['inherited_hardware_sha256'].items():check(B/(B.name+'.sdk')/n,h)
    for base in (B,P):
        m=load(base/'DELIVERY_MANIFEST.json')
        for group in ('source_sha256','proof_sha256'):
            for n,h in m[group].items():check(base/n,h)
    for folder in ('rtl','constraints','ip_repo'):
        for q in files(R/folder):
            # All copied PL source is expected unchanged relative to V1.51,
            # except this version's authored dual-scale additions.
            if q.relative_to(R).as_posix() not in ('rtl/dual_scale_valley.v','rtl/video_bypass.v'):check(q,sha(B/q.relative_to(R)))
    unit=load(O/'candidate_unit.json');assert unit['passed'] and unit['tests']==6
    for n,h in unit['source_sha256'].items():check(R/n,h)
    for p in (O/'dual_scale_vectors/metadata.json',O/'dual_scale_sim/dual_scale.sim/sim_1/behav/xsim/simulate.log',O/'integrated_vectors/metadata.json',O/'integrated_sim/integrated.sim/sim_1/behav/xsim/simulate.log'):
        assert p.exists(),p
    for log,marker in ((O/'dual_scale_sim/dual_scale.sim/sim_1/behav/xsim/simulate.log','PASS DUAL SCALE'),(O/'integrated_sim/integrated.sim/sim_1/behav/xsim/simulate.log','PASS DETECTION')):assert marker in log.read_text(errors='replace')
    cand=load(O/'wide_candidate/result.json');assert cand['status']=='ELIGIBLE_FOR_ISOLATED_RTL_ONLY' and cand['candidate_eligible_for_isolated_rtl'] and not cand['production_changed'] and not cand['board_tested']
    assert cand['checks']['baseline_reproduced'] and cand['checks']['recall_gain_met'] and cand['checks']['precision_floor_met']
    assert load(O/'firmware_audit.json')['passed']
    assert 'All user specified timing constraints are met' in (R/'reports/timing_summary.rpt').read_text()
    assert 'Design State : Fully Routed' in (R/'reports/drc.rpt').read_text()
    assert 'Unsafe  Unknown' in (R/'reports/cdc.rpt').read_text() and '\n' in (R/'reports/cdc.rpt').read_text()
    failure=O/'programming.log';assert failure.exists() and 'target list is empty' in failure.read_text(errors='replace')
    try:
        with urllib.request.urlopen('http://127.0.0.1:8770/api/state?limit=1',timeout=8) as f:live=json.load(f)
    except Exception as e:live=dict(error=str(e))
    save(O/'live_restore_state.json',live)
    assert live.get('revision')=='V1.48'
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();status='HARDWARE_BUILT_BOARD_PROGRAMMING_BLOCKED'
    summary=dict(passed=True,version='V1.52',status=status,deployable=False,completed_at=now,
      scope='Offline candidate passed, fresh routed PL/Vitis artifacts built; physical programming and board validation pending JTAG enumeration',
      live_product='V1.48',hardware_revision='V1.52_BUILD_ONLY',candidate='dual-scale radius8/radius16 weak support',
      candidate_recall_gain_percentage_points=100*(cand['summary']['candidate']['pixel_recall']-cand['summary']['baseline']['pixel_recall']),
      candidate_precision=cand['summary']['candidate']['pixel_precision'],normal_images=230,regression_images=50,
      rtl_sim_pixels=20480,integration_sim_pixels=368640,host_tests=423,
      timing_wns_ns=0.030,timing_whs_ns=0.050,bram_percent=74.64,programming_failure='JTAG target list empty; USB/JTAG device not enumerated',
      bit_sha256=sha(W/'system.bit'),xsa_sha256=sha(W/'system.xsa'),elf_sha256=sha(W/'hdmi_ethernet/build/hdmi_ethernet.elf'),
      backup=plan['backup'],backup_sha256=plan['backup_sha256'])
    save(O/'validation_summary.json',summary);plan.update(phase=status,scope='HARDWARE_BUILT_BOARD_PENDING',deployable=False,live_station='V1.48 restored; V1.52 not programmed');save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase=status,all_build_sessions_completed=True,next_step='When PYNQ-Z2 USB/JTAG enumerates, run activate_v152.ps1, verify V1.52 board identity, then capture narrow and wide recipes on moving HDMI input.'))
    (R/'README.md').write_text(f'''# TileLab V1.52 · 双尺度弱裂纹候选（构建完成，待上板）

V1.52 根据 V1.51 漏检归因增加第二个半径 16 的灰度谷值窗口。半径 8 仍负责建立强裂纹种子，半径 16 只参与四级传播的弱支持，因此 ARM/Vitis 只传递配方参数，检测计算仍在 FPGA 像素流中完成。双尺度通过 bit27 控制，旧配置可复现 V1.48/V1.42 的半径 8 行为。

离线门槛通过：230 张正常图零报警；17 张裂纹和 33 张正常回归保持报警/无报警结果；裂纹像素召回从 {cand['summary']['baseline']['pixel_recall']*100:.2f}% 提升到 {cand['summary']['candidate']['pixel_recall']*100:.2f}%，提升 {summary['candidate_recall_gain_percentage_points']:.2f} 个百分点，精度 {summary['candidate_precision']*100:.2f}%。这是反复使用的开发数据，不能当作工厂盲测准确率。

20,480 像素的双尺度模块仿真和 368,640 像素的完整链路仿真通过，423 项主机测试通过。Vivado 2025.2 综合、布线、XSA/BIT 导出通过；WNS +0.030 ns、WHS +0.050 ns，CDC unsafe=0，BRAM 使用 74.64%。

Vitis 已以新 XSA 构建，ELF 与硬件平台哈希匹配，固件版本目标为 0x12b00。尝试运行烧录脚本时，JTAG 日志返回 `target list is empty`，系统没有枚举 PYNQ-Z2，因此本版暂不标记为实板通过，也没有宣称双尺度已在板上生效。旧 V1.48 工作站已恢复。

板卡重新枚举后，在本目录执行 `scripts/activate_v152.ps1`。脚本会先检查 V1.48 状态、暂停和保存旧工作站，再通过 JTAG 下载 BIT/ELF，随后验证 V1.52 身份。完成身份验证后，再用 `mvtec_hdmi_wide_weak_v152` 和旧 `mvtec_hdmi_weak_v124` 分别测试连续移动画面，比较误报、帧率、传输耗时和红框稳定性。

详细证据在 `reports/v152`，可回退压缩包在 `D:/Vivado/_baseline_backups/tile_v1_51_before_v1_52.zip`。正式技术手册按多轮迭代统一生成。
''',encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for q in files(R/folder):
            if q.suffix not in ('.pid','.log','.pyc','.wdb') and q.name not in ('player_status.json','player_instance.json','display_command.txt'):source[q.relative_to(R).as_posix()]=sha(q)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for q in W.iterdir():
        if q.is_file() and q.suffix in ('.py','.tcl','.bat'):source[q.relative_to(R).as_posix()]=sha(q)
    proofs={R/'README.md',R/'ITERATION_PLAN.json'};proofs.update(q for q in files(O) if q.suffix in ('.json','.log','.txt','.csv','.png'))
    save(R/'DELIVERY_MANIFEST.json',dict(version='V1.52',status=status,deployable=False,created_at=now,baseline=str(B),baseline_manifest_sha256=plan['baseline_manifest_sha256'],backup=plan['backup'],backup_sha256=plan['backup_sha256'],artifacts_sha256=dict(system_bit=sha(W/'system.bit'),system_xsa=sha(W/'system.xsa'),system_ltx=sha(W/'system.ltx'),elf=sha(W/'hdmi_ethernet/build/hdmi_ethernet.elf')),source_sha256=source,proof_sha256={q.relative_to(R).as_posix():sha(q) for q in sorted(proofs)},validation=summary,report='README.md'))
    index=R.parent/'TileLab_进度与回退.md';text=index.read_text(encoding='utf-8');a=text.index('## 尚在进行');b=text.index('## 回退和空间');text=text[:a]+f'| V1.52 | 双尺度弱裂纹：离线门槛、RTL/链路仿真、Vivado/Vitis 构建通过；JTAG 未枚举，待实板 | {status} | [记录]({R.as_posix()}/README.md) |\n\n## 尚在进行\n\nV1.52 构建完成但尚未烧录；V1.48 工作站已恢复。待 USB/JTAG 枚举后完成 V1.52 身份、连续 HDMI 运动和双配方对照，再决定是否发布。\n\n'+text[b:];index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(passed=True,status=status,deployable=False,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()
