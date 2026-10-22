from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET,gzip
R=Path('D:/Vivado/TileLab_SingleTile_V164_20261019');P=R/'project/pynq_z2_tile_v1_53';W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
def put(src,dst):
    src=Path(src);dst=Path(dst)
    if not src.exists():return
    dst.parent.mkdir(parents=True,exist_ok=True);raw=src.read_bytes()
    if len(raw)>120000:
        zipped=dst.with_name(dst.name+'.gz');zipped.write_bytes(gzip.compress(raw,mtime=0));assert gzip.decompress(zipped.read_bytes())==raw
        dst.with_name(dst.name+'.tail.txt').write_text(raw.decode('utf8',errors='replace')[-20000:],encoding='utf8')
        records.append(dict(original=str(src),saved=str(zipped.relative_to(R)),uncompressed_bytes=len(raw),uncompressed_sha256=sha(src)))
    else:shutil.copy2(src,dst)
def copy_folder_files(src,dst,names):
    for n in names:put(src/n,dst/n)
for n,label in [(176,'hw03_125mhz_rejected'),(178,'hw01_125mhz_rejected')]:
    hw=W/('v176_hw03' if n==176 else 'v178_hw01');out=P/f'reports/v{n}/{label}'
    copy_folder_files(hw,out,['implementation_status.json','timing_summary.rpt','utilization.rpt','clocks.rpt','drc.rpt','candidate_preflight.json','optimization_strategy.json'])
    if n==176:
        copy_folder_files(hw/'physical_repair01',out/'single_repair',['implementation_status.json','timing_summary.rpt','utilization.rpt','clocks.rpt','drc.rpt','bus_skew.rpt'])
        put(W/'v176_physical_pipeline03.json',out/'pipeline.json')
    else:
        put(W/'v178_physical_pipeline01.json',out/'prebuild_reference_error.json');put(W/'v178_physical_pipeline02.json',out/'pipeline.json')
experiments=[(177,54,'v177_all_c01'),(178,55,'v178_all_c01'),(178,56,'v178_all_c01'),(179,57,'v179_all_c01'),(179,58,None),(179,59,'v179_all_c03'),(179,60,'v179_all_c04'),(179,61,'v179_all_c05'),(179,62,'v179_all_c05')]
table=[]
for version,index,reg in experiments:
    out=P/f'reports/v{version}/hls{index}';hls=W/f'v170_hls{index}';source=P/f'experimental/texture_v170/hls/frozen/v170_hls{index}.cpp'
    item=dict(hls=index,source_sha256=sha(source),scope='DEVELOPMENT_EXPERIMENT_NOT_BOARD_ACCEPTED',board_programmed=False)
    xml=hls/'solution/syn/report/texture_integer_csynth.xml'
    if xml.exists():
        put(xml,out/'csynth.xml');root=ET.fromstring(xml.read_bytes())
        item.update(estimated_clock_ns=float(root.findtext('./PerformanceEstimates/SummaryOfTimingAnalysis/EstimatedClockPeriod')),hls_resources={c.tag:int(c.text) for c in root.find('./AreaEstimates/Resources')})
    if reg and (W/reg/'summary.json').exists():
        summary=json.loads((W/reg/'summary.json').read_text());assert summary['source_sha256']==sha(source)
        assert summary['cases']==summary['correct']==117 and summary['all_grid_values_exact'] and summary['all_original_size_masks_exact']
        put(W/reg/'summary.json',out/'full_c_summary.json');put(W/reg/'results.json',out/'full_c_results.json')
        compared=[]
        for case in sorted((W/reg).iterdir()):
            if not case.is_dir():continue
            a=case/'result.bin';b=W/'v173_all_c10'/case.name/'result.bin'
            if not a.exists():continue
            assert a.read_bytes()==b.read_bytes(),(reg,case.name)
            compared.append(dict(id=case.name,result_sha256=sha(a),bytes=a.stat().st_size))
        assert len(compared)==117
        item.update(full_c_all_117_exact=True,complete_output_byte_comparison=dict(baseline='v173_all_c10',cases=117,all_identical=True))
        out.mkdir(parents=True,exist_ok=True);(out/'complete_output_manifest.json').write_text(json.dumps(compared,indent=2)+'\n')
    else:item['full_c_all_117_exact']=False
    cosim=hls/'solution/sim/report/texture_integer_cosim.rpt'
    if cosim.exists():put(cosim,out/'cosim.rpt');item['reduced_full_function_cosim_pass']='|      Pass|' in cosim.read_text()
    exports=list((hls/'solution/impl/ip').glob('*.zip')) if (hls/'solution/impl/ip').exists() else []
    item['ip_exports']=[dict(filename=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in exports]
    if index in [58,60]:
        put(W/f'v170_hls{index}_console.log',out/'failed_console.log')
        put(hls/'solution/.autopilot/db/autopilot.flow.log',out/'failed_frontend_flow.log')
    if index==57:item['rejected_reason']='12.860ns HLS estimate: moving a wide multiply to fabric without internal decomposition fails the clock goal'
    if index==58:item['rejected_reason']='C type ambiguity in signed conditional expression; superseded by frozen59, no RTL or board'
    if index==60:item['rejected_reason']='C117 exact but HLS legacy frontend crashes before scheduling; superseded by inline same-arithmetic61, no RTL or board'
    out.mkdir(parents=True,exist_ok=True);(out/'experiment.json').write_text(json.dumps(item,indent=2)+'\n');table.append(item)
for name in ['v177_recurrence54.json','v178_recurrence55.json','v178_spatial_proof01.json','v178_hls56_full_pipeline.json','v179_recurrence59.json','v179_hls62_full_pipeline.json']:
    put(W/name,P/('reports/v'+name[1:4]+'/checks/'+name))
for name in ['v177_recurrence_negative01','v178_spatial_negative01']:
    for p in (W/name).glob('*.json'):put(p,P/('reports/v'+name[1:4]+'/checks/'+name)/p.name)
for name in ['bilinear','normalize','requant']:
    copy_folder_files(W/('v179_scalar61_'+name),P/('reports/v179/scalar61/'+name),['summary.json','test.log'])
for name in ['test_v179_scalar61.py','start_v179_hls62_full.py','prepare_v179_hls61.py','start_v179_physical01.py','archive_v179_checkpoint.py']:
    put(W/name,P/'reports/v179/reproduction'/name)
out=P/'reports/v179';out.mkdir(parents=True,exist_ok=True)
(out/'experiment_table.json').write_text(json.dumps(table,indent=2)+'\n')
(out/'compressed_log_manifest.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(dict(experiments=len(table),full_c_cases=[(x['hls'],x['full_c_all_117_exact']) for x in table],compressed_logs=len(records),latest=table[-1])))
