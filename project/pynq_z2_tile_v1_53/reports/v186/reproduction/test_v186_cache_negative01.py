from pathlib import Path
import importlib.util,json,shutil,re
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
spec=importlib.util.spec_from_file_location('cachecheck',P/'tools/fpga_texture_v170/check_normal_cache.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
out=W/'v186_cache_negative01';out.mkdir(exist_ok=False);root=out/'fixture'
files=['src/texture_integer.cpp','solution/syn/verilog/texture_integer.v']+['solution/syn/verilog/texture_integer_'+n+'_RAM_2P_BRAM_1R1W.v' for n in ['line','normal_line']]
for name in files:
 f=root/name;f.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(W/'v170_hls70'/name,f)
assert mod.inspect(root)['passed'] and mod.inspect(W/'v170_hls69') is None
tests=[('source_width','src/texture_integer.cpp','ap_uint<24> normal_line[224];','ap_uint<23> normal_line[224];'),
 ('source_depth','src/texture_integer.cpp','normal_line[224]','normal_line[223]'),
 ('old_writer','src/texture_integer.cpp','if(c==2)normal_line[x]=normalized;','if(c==2)line[x]=normalized;'),
 ('upper_bits','src/texture_integer.cpp','pack_t(normal_line[x]);','pack_t(normal_line[x])|(pack_t(1)<<31);'),
 ('generated_width','solution/syn/verilog/texture_integer_normal_line_RAM_2P_BRAM_1R1W.v','parameter DataWidth = 24;','parameter DataWidth = 23;')]
results=[]
for name,path,a,b in tests:
 f=root/path;s=f.read_text();assert a in s;f.write_text(s.replace(a,b))
 try:
  try:mod.inspect(root)
  except ValueError as e:results.append(dict(case=name,rejected=True,reason=str(e)))
  else:raise AssertionError(name+' unexpectedly accepted')
 finally:f.write_text(s)
f=root/'solution/syn/verilog/texture_integer.v';s=f.read_text();block=re.search(r'\bline_U\((.*?)\n\);',s,re.S).group();new=re.sub(r'\.we1\(grp_conv_fu_\d+_line_r_we1\)', '.we1(normal_line_we1)',block);assert block!=new
f.write_text(s.replace(block,new))
try:
 try:mod.inspect(root)
 except ValueError as e:results.append(dict(case='shared_write_enable',rejected=True,reason=str(e)))
 else:raise AssertionError('Shared control accepted')
finally:f.write_text(s)
assert mod.inspect(root)['passed'];j=dict(scope='MUTATED_CACHE_SEPARATION_GUARD_REJECTIONS_NOT_BOARD',passed=True,legacy_hls69_returns_none=True,cases=results)
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
