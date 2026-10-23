from pathlib import Path
import importlib.util,json,shutil
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
spec=importlib.util.spec_from_file_location('quartercheck',P/'tools/fpga_texture_v170/check_quarter_pipeline.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
out=W/'v185_structure_negative01';out.mkdir(exist_ok=False);root=out/'fixture'
files=['src/texture_integer.cpp','solution/syn/verilog/texture_integer.v']
for name in ['quarter_horizontal','quarter_vertical']:
 files+=['solution/syn/verilog/texture_integer_'+name+'.v','solution/syn/report/'+name+'_csynth.xml']
for name in files:
 f=root/name;f.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(W/'v170_hls68'/name,f)
assert mod.inspect(root)['passed'] and mod.inspect(W/'v170_hls66') is None
cases=[('horizontal_width','solution/syn/verilog/texture_integer_quarter_horizontal.v','[11:0] ap_return;','[10:0] ap_return;'),
 ('vertical_width','solution/syn/verilog/texture_integer_quarter_vertical.v','[11:0] top;','[10:0] top;'),
 ('latency','solution/syn/report/quarter_vertical_csynth.xml','<Worst-caseLatency>2</Worst-caseLatency>','<Worst-caseLatency>1</Worst-caseLatency>'),
 ('dsp_budget','solution/syn/report/quarter_horizontal_csynth.xml','<DSP>0</DSP>','<DSP>1</DSP>'),
 ('rounding','src/texture_integer.cpp','return i8(v<0?-((-v+8)>>4):((v+8)>>4));','return i8(v>>4);')]
results=[]
for name,path,a,b in cases:
 f=root/path;original=f.read_text();assert a in original,(name,a);f.write_text(original.replace(a,b))
 try:
  try:mod.inspect(root)
  except ValueError as e:results.append(dict(case=name,rejected=True,reason=str(e)))
  else:raise AssertionError('Bad quarter structure accepted: '+name)
 finally:f.write_text(original)
f=root/'solution/syn/verilog/texture_integer.v';original=f.read_text();a='texture_integer_quarter_vertical grp_quarter_vertical';assert a in original
f.write_text(original.replace(a,'unused_quarter_vertical grp_quarter_vertical',1))
try:
 try:mod.inspect(root)
 except ValueError as e:results.append(dict(case='parallel_instance_missing',rejected=True,reason=str(e)))
 else:raise AssertionError('Missing parallel instance accepted')
finally:f.write_text(original)
assert mod.inspect(root)['passed'];j=dict(scope='MUTATED_GENERATED_QUARTER_GUARD_REJECTIONS_NOT_BOARD',passed=True,legacy_hls66_returns_none=True,cases=results)
(out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
