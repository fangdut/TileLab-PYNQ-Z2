"""Release metadata: require actual matching hardware, tests and rendered report."""
from pathlib import Path
import datetime,hashlib,json
R=Path(__file__).resolve().parents[1];T=R/'reports/v15';W=R/'pynq_z2_tile_v1_5.sdk'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
H=read(T/'real_board/summary.json');Q=read(T/'recipe_boundary/result.json')
C=read(T/'continuous/ultrafast_60s.json');V=read(T/'continuous/real_video_120s.json')
M=read(T/'motion_evidence_audit.json');B=read(T/'benchmark/results.json')
P=read(T/'preserved_records.json');build=read(T/'build_metrics.json')
live=read(T/'delivery_live_state.json');qa=read(T/'document_qa.json')
assert all(j['passed'] for j in (H,Q,C,V,live))
assert all(v['functional_pass'] for v in M.values())
assert qa['all_pages_visually_checked']
assert read(T/'ui_checks.json')['status'].startswith('PASS')
program=read(R/'reports/programmed_v15.json')
for name,digest in program['sha256'].items():assert sha(W/name)==digest
assert program==read(T/'programmed_acceptance.json')
assert all(j['before']['boot_id']==program['boot_id'] for j in (H,C,V,live))
assert H['before']['version']==0x10500
assert len(H['counts'])==2 and H['samples']==50
assert 'All user specified timing constraints are met' in (R/'reports/timing_summary.rpt').read_text()
assert 'PASS continuous SG' in (T/'sg_integration.log').read_text()
assert 'PASS' in (T/'tracker_simulation_final.log').read_text()
assert 'PASS' in (T/'gate_band.log').read_text()
assert 'OK' in (T/'host_final_tests.log').read_text()
assert read(T/'native_sg/result.json')['result']=='PASS'
rtl=read(T/'rtl_equivalence.json')
rtl['sha256']={p.relative_to(R).as_posix():sha(p) for p in (R/'rtl').glob('*.v')}
rtl['raw_byte_changed_sources']=[name for name,digest in rtl['sha256'].items() if sha(Path(rtl['baseline'])/name)!=digest]
def normalized_lines(p):return p.read_text(encoding='utf-8-sig').splitlines()
rtl['changed_sources']=[name for name in rtl['sha256'] if normalized_lines(Path(rtl['baseline'])/name)!=normalized_lines(R/name)]
rtl['encoding_or_line_ending_only']=[name for name in rtl['raw_byte_changed_sources'] if name not in rtl['changed_sources']]
assert set(rtl['changed_sources'])=={'rtl/product_tracker.v','rtl/frame_capture_sg.v'}
rtl['note']='Line-by-line text comparison removes only UTF-8 BOM and line terminators; five other files differ only in encoding/line endings. Exact byte hashes are retained separately. Pixel detector and packet datapath retained. Product statistics now use a 64-column presence band; best-frame ranking is completeness then center distance, with candidate-area tie-break.'
(T/'rtl_equivalence.json').write_text(json.dumps(rtl,indent=2))
evidence=['real_board/summary.json','real_board/results.json','recipe_boundary/result.json','continuous/ultrafast_60s.json','continuous/real_video_120s.json','motion_evidence_audit.json','benchmark/results.json','benchmark/calibration.json','benchmark/dataset_audit.json','build_metrics.json','rtl_equivalence.json','preserved_records.json','baseline_preservation.json','v14_handoff.json','programmed_acceptance.json','delivery_live_state.json','ui_checks.json','document_qa.json','host_final_tests.log','tracker_simulation_final.log','sg_integration.log','native_sg/ownership_result.json']
evidence=[p.replace('native_sg/ownership_result.json','native_sg/result.json') for p in evidence]
evidence += ['hdmi_calibration/calibration.json','video_calibration/calibration.json','training_input_gains.json','pre_input_calibration/real_board/summary.json','pre_input_calibration/real_video_120s.json']
evidence += ['gate_band.log','gate_diagnostic.json','gate_figure_source.json','gate_training_audit.json','pre_gate_band/physical_identity_audit.json','startup_race_recipe.log','pre_player_fix/motion_evidence_audit.json','continuous/real_video_20s.json']
evidence += ['pre_player_priority/motion_evidence_audit.json']
evidence += ['user_display_feedback.json','workstation_final.png']
assert all((T/p).exists() for p in evidence), 'Required release evidence missing'
sources=[]
for folder in ('rtl','constraints','sim','scripts','models','host'):
 sources.extend(p for p in (R/folder).rglob('*') if p.suffix in {'.v','.sv','.xdc','.py','.tcl','.ps1','.bat','.html','.json','.cs'} and '__pycache__' not in p.parts and not any(x in p.name for x in ('status','pid','command')) and 'legacy_reference' not in p.parts)
sources.extend(p for p in (W/'ethernet_sources').iterdir() if p.is_file())
sources.extend(p for p in W.iterdir() if p.suffix in {'.py','.tcl','.bat'})
sources.extend([R/'README.md',R/'启动以太网工作站.bat',R/'data/DATA_SOURCES.md'])
metrics=dict(real_static=H,synthetic_motion={k:C[k] for k in ('seconds','raw_capture_fps','host_captures','saved_events','max_interval_ms','p99_interval_ms')},real_motion={k:V[k] for k in ('seconds','raw_capture_fps','host_captures','saved_events','max_interval_ms','p99_interval_ms')},motion_audit={k:{a:b for a,b in v.items() if a!='items'} for k,v in M.items()},build=build)
summary=dict(version='V1.5',status='BOARD_VALIDATED_WITH_CENTERING_LIMIT' if not all(v['passed'] for v in M.values()) else 'BOARD_VALIDATED_MATERIAL_SPECIFIC_PROTOTYPE',all_performance_targets_met=all(v['passed'] for v in M.values()),metrics=metrics,classification=B['summary'],evidence=evidence)
(T/'final_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=dict(version='Tile V1.5',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=summary['status'],programming=program,metrics=metrics,
 sources_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(set(sources))},
 report_sha256={p.relative_to(R).as_posix():sha(p) for p in (R/'docs').glob('Tile_V1.5*')},
 evidence_sha256={('reports/v15/'+p):sha(T/p) for p in evidence},
 preservation=dict(project=read(T/'baseline_preservation.json'),records=P),
 datasets=dict(total_photographs=2114,calibration=230,evaluated=1884,sources='data/DATA_SOURCES.md',audit=read(T/'benchmark/dataset_audit.json')),
 limits=['Normal-texture suppression trades off weak-crack recall; no universal industrial accuracy claim','MVTec test images were previously viewed and are historical regression, not blind validation','Roof tiles contain limited physical specimens and non-crack defects; facade images include grout lines','Runtime FPGA pipeline remains 720p60; host preview is sampled due to Ethernet bandwidth','One lane, bright separated products on a dark belt; no tightly packed products','Twelve pending events and volatile DDR; power loss and prolonged paused receiver can lose data','HDMI boxes use previous-frame locations; saved PC evidence uses same-frame locations','Five inherited HDMI CDC unsafe endpoints require further review','Unlicensed Ceramic Cracks originals and derived previews must be excluded from redistribution'])
if not all(v['passed'] for v in M.values()):manifest['limits'].insert(0,'The original 32 px high-speed centering goal remains unmet; strict motion audit is false. Complete one-per-product capture passes separately. See measured center errors.')
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(status=manifest['status'],source_files=len(manifest['sources_sha256']),metrics=metrics),ensure_ascii=False))
