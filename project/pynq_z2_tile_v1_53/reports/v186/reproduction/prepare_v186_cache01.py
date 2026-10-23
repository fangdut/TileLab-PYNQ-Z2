from pathlib import Path
import hashlib,json
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
base=P/'experimental/texture_v170/hls/frozen/v170_hls69.cpp';s=base.read_text();assert hashlib.sha256(base.read_bytes()).hexdigest()=='ca83b961ae8ec3a34a0bf3be25ec87e45d7afbc60ae05b9e2fd4d12b39a8e36b'
old='    uint64_t ram[O][RD];pack_t line[LD];uint32_t row0[1024],row1[1024];unsigned raw[3136],smooth[3136];';assert s.count(old)==1
s=s.replace(old,old+'\n    // Separate RGB normalization staging from the128-bit CNN line memory.\n    // Each normalized pixel has only three signed8 components; upper104bits\n    // were always zero before. A dedicated24-bit cache removes a distant\n    // preprocessing writer from the measured convolution BRAM-enable path.\n    ap_uint<24> normal_line[224];\n#pragma HLS BIND_STORAGE variable=normal_line type=ram_2p impl=bram')
for a,b in [('        pack_t normalized=0;','        ap_uint<24> normalized=0;'),('if(c==2)line[x]=normalized;','if(c==2)normal_line[x]=normalized;'),('work[y*side+x]=line[x];','work[y*side+x]=pack_t(normal_line[x]);')]:
 assert s.count(a)==1,a;s=s.replace(a,b)
s=s.replace('// Reuse the CNN line BRAM as a normalized-row staging buffer.','// Dedicated compact normalization staging keeps CNN line controls local.')
b=P/'experimental/cache_split_v186';b.mkdir(exist_ok=False);source=b/'texture_cache_split.cpp';source.write_text(s)
frozen=P/'experimental/texture_v170/hls/frozen/v170_hls70.cpp';assert not frozen.exists();frozen.write_bytes(source.read_bytes())
tcl=(P/'experimental/quarter_pipeline_v185/build_hls.tcl').read_text().replace('v170_hls68.cpp','v170_hls70.cpp').replace('quarter_pipeline_v185/texture_quarter_pipeline.cpp','cache_split_v186/texture_cache_split.cpp');(b/'build_hls.tcl').write_text(tcl)
for oldfile,newfile,pairs in [('start_v185_quarter_full_c.py','start_v186_cache_full_c.py',[('v185_quarter_full_c.log','v186_cache_full_c.log'),('quarter_pipeline_v185/texture_quarter_pipeline.cpp','cache_split_v186/texture_cache_split.cpp'),('v185_full_c01','v186_full_c01'),('v185_all_c01','v186_all_c01')]),('start_v185_hls68_synth.py','start_v186_hls70_synth.py',[('v170_hls68','v170_hls70'),('quarter_pipeline_v185/build_hls.tcl','cache_split_v186/build_hls.tcl')])]:
 t=(W/oldfile).read_text()
 for a,c in pairs:assert a in t;t=t.replace(a,c)
 f=W/newfile;assert not f.exists();f.write_text(t)
proposal=dict(scope='ROUTED_SHARED_BRAM_CONTROL_CACHE_SPLIT_PROPOSAL_NOT_BOARD',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),base_source_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),model_changed=False,threshold_changed=False,input_resolution_changed=False,measured_path='V185125MHz:convloop421init->global128bit line_U enable,-0.786nssetup,8.111nsdata/75.649%route',change='Dedicated224x24bit normalized RGB row cache; CNN2048x128 line buffer retains convolution ownership only. Exact zero-extension restores original128bit packed RGB words.',added_logical_storage_bits=224*24,accuracy_or_speed_claimed=False)
(b/'proposal.json').write_text(json.dumps(proposal,indent=2)+'\n');print(json.dumps(proposal))
