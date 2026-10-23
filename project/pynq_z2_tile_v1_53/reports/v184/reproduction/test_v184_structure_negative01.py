from pathlib import Path
import importlib.util,json,shutil
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
spec=importlib.util.spec_from_file_location('rowcheck',P/'tools/fpga_texture_v170/check_row_address.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
out=W/'v184_structure_negative01';out.mkdir(exist_ok=False);root=out/'fixture'
files=['src/texture_integer.cpp','solution/syn/verilog/texture_integer.v','solution/syn/verilog/texture_integer_row_offset.v','solution/syn/verilog/texture_integer_mul_11ns_10ns_21_4_0.v','solution/syn/report/row_offset_csynth.xml']
for name in files:
 f=root/name;f.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(W/'v170_hls66'/name,f)
assert mod.inspect(root)['passed'] and mod.inspect(W/'v170_hls65') is None
cases=[('width','solution/syn/verilog/texture_integer_row_offset.v','[9:0] row;','[8:0] row;'),
 ('input_register','solution/syn/verilog/texture_integer_mul_11ns_10ns_21_4_0.v','din0_reg <= din0;','din0_reg <= din0 + 1;'),
 ('latency','solution/syn/report/row_offset_csynth.xml','<Worst-caseLatency>3</Worst-caseLatency>','<Worst-caseLatency>2</Worst-caseLatency>'),
 ('guard','src/texture_integer.cpp','width>1024||height>1024','width>2048||height>2048'),
 ('unused_helper','solution/syn/verilog/texture_integer.v','texture_integer_row_offset grp_row_offset','unused_row_offset grp_row_offset')]
results=[]
for name,path,a,b in cases:
 f=root/path;original=f.read_text();assert a in original,(name,a);f.write_text(original.replace(a,b))
 try:
  try:mod.inspect(root)
  except ValueError as e:results.append(dict(case=name,rejected=True,reason=str(e)))
  else:raise AssertionError('Bad structure accepted: '+name)
 finally:f.write_text(original)
f=root/'solution/syn/verilog/fake_old_mul.v';f.write_text('// mul_22s_32s_32 present again\n')
try:
 try:mod.inspect(root)
 except ValueError as e:results.append(dict(case='old_wide_multiplier',rejected=True,reason=str(e)))
 else:raise AssertionError('Old wide multiplier accepted')
finally:f.unlink()
assert mod.inspect(root)['passed']
j=dict(scope='MUTATED_GENERATED_ROW_GUARD_REJECTIONS_NOT_BOARD',passed=True,legacy_hls65_returns_none=True,cases=results)
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
